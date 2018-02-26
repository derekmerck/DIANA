import requests
import os
import logging

def splunk_xml2pdf(fn, splunkhost, splunkuser, splunkpass, tokens={}):

    with open(fn, 'rb') as XMLfile:
        XMLDashboard = XMLfile.read().replace('\n', '')
        XMLDashboard = XMLDashboard.replace('&lt;', '%26lt%3B')  # Have to pre-encode this before url encoding

    # Replace all tokens in the XMLCode
    for t in tokens.keys():
        XMLDashboard = XMLDashboard.replace('$'+t+'$', tokens[t])

    # Send XML code to endpoint, answer should be a pdf file
    r = requests.get('https://{0}:8089/services/pdfgen/render'.format(splunkhost),
                     auth=(splunkuser, splunkpass),
                     params={'input-dashboard-xml': XMLDashboard, 'paper-size': 'a4-landscape'},
                     verify=False)

    logging.debug(r)

    # Send XML code to endpoint, answer should be a pdf file
    if r.status_code == 200:
        fno = '{0}.pdf'.format( os.path.splitext(os.path.basename(fn))[0])
        logging.debug(fno)
        with open(fno, 'wb') as pdffile:
            pdffile.write(r.content)
