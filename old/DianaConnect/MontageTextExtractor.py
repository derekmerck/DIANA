import sys
from Tkinter import *
import tkFileDialog
import re
import json
import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup

def msg_popup(s):
	win = Toplevel()
	win.wm_title("Alert")
	l = Label(win, text=s)
	l.grid(row=0, column=0)
	b = Button(win, text="Okay", command=win.destroy)
	b.grid(row=1, column=0)

def getdata():
	global e1, e2, e3, e4, e5, e6
	ls_id = e1.get()
	ls_pw = e2.get()
	montage_id = e3.get()
	montage_pw = e4.get()
	
	accessions = e5.get()
	accessions = accessions.split(",")
	
	#FIELD EXTRACTION METHOD #1 - HARD-CODING
	#terms = 'Patient height,Patient weight,Body surface area,End-diastolic septal wall thickness,BASAL SHORT AXIS,MID-CAVITY SA,APICAL SA,TRUE APEX,LV EDV,LV ESV,LV EF,Pericardium,Mitral Valve,Tricuspid Valve,Aortic Valve,THORACIC AORTA,PULMONARY ARTERIES'
		
	#FIELD EXTRACTION METHOD #2 - GET ALL POSSIBLE TERMS USING FIRST FIVE ACCESSIONS AS TEMPLATE
		#BY LOCATING ':' AND ABSTRACTING WORDS TO THE LEFT OF IT
	possibleterms=''
	for x in range(0, 5):
		if x < len(accessions):
			with requests.Session() as s:
				# Establish remote connection to Lifespan VPN
				requestURL = 'https://remote.lifespan.org/dana-na/auth/url_default/login.cgi'
				data = {'tz_value': '-300', 'realm': 'Users', 'username': ls_id, 'password': ls_pw}
				r = s.post(requestURL, data=data, verify=False)
				h = BeautifulSoup(r.content, 'html.parser')
				dsid_field = h.find(id='DSIDFormDataStr')
				data = {dsid_field['name']: dsid_field['value'], 'btnContinue': 'Continue%20the%20session'}
				ls_status = s.post(requestURL, data=data)

				# Query Montage for individual accession number
				requestURL = 'https://remote.lifespan.org/,DanaInfo=lsradmontage.lsmaster.lifespan.org/api/v1/index/rad/search/?q='+ accessions[x] + '&format=json'
				r = s.get(requestURL , auth=HTTPBasicAuth(montage_id, montage_pw))
				output =r.json()

			i=0
			while i < len(output['objects']):
				# Isolate the result that matches search criteria of accession number and exam code
				# Query results technically should only be one study, but this confirms accession number/exam code query
				resultaccession =output['objects'][i]['accession_number']
				if (resultaccession == accessions[x]):
					examtext=re.sub('<[^>]+>', '', output['objects'][i]['text'])
					examlines = examtext.split('\r')
					for line in examlines:
						if ':' in line: 
							matchoutput=line.split(':')
							matchoutput1= matchoutput[0].replace(",", " ")
							possibleterms = possibleterms + matchoutput1 + ","
				i=i+1
	possibleterms = possibleterms.split(',')
	possibleterms = list(set(possibleterms))
	possibleterms = map(str, possibleterms)
	possibleterms = sorted(possibleterms, key=str.lower)
	
	master = Tk()
	lb = Listbox(master, height=30, selectmode=EXTENDED)
	lb.pack()
	for i,possibleterm in enumerate(possibleterms):
		lb.insert(END, possibleterm)  
	Button(master, text='Select', command=master.quit).pack()
	master.mainloop()
	items = lb.curselection()
	terms = ''
	for i in items:
		terms = terms + possibleterms[i] + ","
		
	#FIELD EXTRACTION METHOD #3 - USER INPUT (OVERRIDES METHOD #2)
	if (str(e6.get()) != ''):
		terms = e6.get()
		

	#BEGIN EXTRACTING DATA FOR CSV EXPORT
	
	#constructing csv row 1 header
	selectedterms = terms.split(",")
	csv="Patient MRN, Accession Number, Exam Code, Exam Description, "
	for term in selectedterms:
		csv = csv + term + ", "
	csv = csv + "\n"
	progress=0
	for k, accessionnum in enumerate(accessions):
		with requests.Session() as s:

			# Establish remote connection to Lifespan VPN
			requestURL = 'https://remote.lifespan.org/dana-na/auth/url_default/login.cgi'
			data = {'tz_value': '-300', 'realm': 'Users', 'username': ls_id, 'password': ls_pw}
			r = s.post(requestURL, data=data, verify=False)
			h = BeautifulSoup(r.content, 'html.parser')
			dsid_field = h.find(id='DSIDFormDataStr')
			data = {dsid_field['name']: dsid_field['value'], 'btnContinue': 'Continue%20the%20session'}
			s.post(requestURL, data=data)

			# Query Montage for individual accession number
			requestURL = 'https://remote.lifespan.org/,DanaInfo=lsradmontage.lsmaster.lifespan.org/api/v1/index/rad/search/?q='+ accessionnum + '&format=json'
			r = s.get(requestURL , auth=HTTPBasicAuth(montage_id, montage_pw))
			output =r.json()

			i=0
			while i < len(output['objects']):
				# Isolate the result that matches search criteria of accession number and exam code
				# Query results technically should only be one study, but this confirms accession number/exam code query
				resultaccession =output['objects'][i]['accession_number']
				if (resultaccession == accessionnum):
					acc=output['objects'][i]['accession_number']
					mrn=output['objects'][i]['patient_mrn']
					examcode=output['objects'][i]['exam_type']['code']
					examdesc=output['objects'][i]['exam_type']['description']
					examtext=re.sub('<[^>]+>', '', output['objects'][i]['text'])
					csv = csv + mrn + ", "
					csv = csv + acc + ", "
					csv = csv + examcode + ", "
					csv = csv + examdesc + ", "
					examlines = examtext.split('\r')
					for term in selectedterms:
						for line in examlines:
							value=''
							termcolon = term + ':'
							if termcolon in line: 
								matchoutput=line.split(':')
								matchoutput1= matchoutput[1].replace(",", " ")
								value=matchoutput1
								break
						csv = csv + value + ", "
								
				i=i+1
		csv = csv + "\n"
		print "%d of %d\n" %(k,len(accessions))
	
	f = tkFileDialog.asksaveasfile(mode='w', defaultextension=".csv")
	if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
		return
	text2save = csv
	f.write(text2save)
	f.close()
	msg_popup('CSV file created!')
	print 'CSV file created!'
	
root = Tk()

root.title('Montage Text Extractor v1')

Label(root, text="Lifespan ID").grid(row=0)
Label(root, text="Lifespan Pass").grid(row=1)
Label(root, text="Montage ID").grid(row=2)
Label(root, text="Montage Pass").grid(row=3)
Label(root, text="Accession #s").grid(row=4)
Label(root, text="Fields of Interest (FOI)").grid(row=5)
Label(root, text="*Multiple entries must be comma separated").grid(row=6, column=1)
Label(root, text="**If FOIs are unknown, please leave blank. Any entries will override selections made in next step.").grid(row=7, column=1)
e1 = Entry(root, width=50)
e1.grid(row=0, column=1)
e2 = Entry(root, show="*", width=50)
e2.grid(row=1, column=1)
e3 = Entry(root, width=50)
e3.grid(row=2, column=1)
e4 = Entry(root, show="*", width=50)
e4.grid(row=3, column=1)
e5 = Entry(root, width=50)
e5.grid(row=4, column=1)
e6 = Entry(root, width=50)
e6.grid(row=5, column=1)
possibleterms = ''
b = Button(root,text='Okay',command=getdata)
b.grid(row=8,column=1)
e1.focus_set()
root.mainloop()
