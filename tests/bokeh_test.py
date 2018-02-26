import dateutil.parser
import csv
from bokeh.plotting import figure, output_file, show
from splunklib import client, results

# Create a Service instance and log in
splunk = client.connect(host="trusty64",
               port=8089,
               username="admin",
               password="5plunK!")


# Run a one-shot search and display the results using the results reader

# Set the parameters for the search:
kwargs_oneshot = {"earliest_time": "1995-01-01T12:00:00.000",
                  "latest_time": "now",
                  "count": 0,
                  "output_mode": "csv"}
searchquery_oneshot = "search index=dicom host=*8047 | dedup AccessionNumber | bin _time span=1months | chart count by _time"

oneshotsearch_results = splunk.jobs.oneshot(searchquery_oneshot, **kwargs_oneshot)

reader = csv.reader(oneshotsearch_results)
dates = []
counts = []

output_file("datetime.html")

next(reader, None)
next(reader, None)
for row in reader:
    print row
    dates.append(dateutil.parser.parse(row[0]))
    counts.append(row[1])

# create a new plot with a datetime axis type
p = figure(plot_width=800, plot_height=250, x_axis_type="datetime")

# Comes in 3 month chunks as of now, convert 3 mo to ms for width
p.vbar(x=dates, bottom=0, top=counts, color='blue', width=0.9*30*24*60*60*1000)

show(p)