# OCI-Archive-Log-Restore
OCI Logging Service is a comprehensive, centralized, and fully managed service for all your infrastructure and application log data. You can enable automatic archiving to export old data to low-cost, durable Object Storage in accordance with your data management requirements. But what happens when you need to perform searches on archived data? OCI Logging service does not yet provide the ability to directly search archived log content. That's ok, because with a simple utility you can quickly and easily restore archived log data content to the Logging service repository for immediate searching.

This Python file is easy to customize for special workload requirements, but for now let’s keep it simple. Execute this utility in your OCI Cloud Shell session to automatically inherit permissions to make OCI Service API calls.  It does require a few command line parameters. First, locate the Object Storage bucket(s) and folder(s) that contain the archive log files you would like to restore. You may need to review the Service Connector description to determine this location. 

# Required parameters:
--compartment (or simply -c ) The Compartment OCID where your archive log Object Storage bucket is located. Example: ocid1.compartment.oc1..ae3zfvlnkmruyc3pdd6rtfondntk7gjezf

--bucket (or simply -b ) The name of the Object Storage bucket that contains you target archived log file objects.

--folder (or simply -f ) The prefix assigned to archived log objects. This was generated by the Service Connector and is part of the full object name; however, it gives the appearance of a file system folder structure. 

# Optional parameters
Default values will be used if not specified in the execution command but review these default values to ensure they are appropriate for your use case.

--start (or simply -s ) Timestamp for designating the starting point for the search period. This filters the original log timestamps to determine which entries should be restored. If no parameter is given, this defaults to 24 hours in the past. Yes, probably not the most common starting time for restoring actual archives, however this works for testing newly created archive connector streams. Log content must be archived, but not necessarily aged out of the Logging service. Restored log content is staged in a new designated log container and will not alter active logs.
Use this format: 'year-month-day hours:minutes:seconds'   Example: '2019-11-05 02:10:00'

--end (or simply -e ) Timestamp for designating the end point for the search period. If no parameter is given, this defaults to the current time. Note: this utility is set to restore 1000 log archive objects per execution. This may represent 3 or 4 days for low volume logs, and considerably less for busy logs. You can adjust the restore batch size in the Python code, however, keep in mind the potential system load and process duration when selecting the search time period.
Use this format: 'year-month-day hours:minutes:seconds'  Example: '2019-11-06 00:00:00'

--logname (or simply -l ) This is the new Logging service log name used as the restoration location. Multiple archived logs could share a single restored log container, however, consider separating restored content if that improves the ease of searching and analysis. Default, if not specified: archive-restore-log

# Example commands
Skipping optional parameters (Compartment OCID and Folder name shortened for readability):
$ python3 log-restore.py --compartment=ocid1.compartment.oc1..aaaaaaaappw5e37gjezfrosagy7ja --bucket=logarchive01 --folder=ocid1.serviceconnector.oc1.ca-montreal-1.amaaaaaauwpiejqaqk37cfqvrxhfcerepboq --start='2019-11-05 02:10:00' --end='2019-11-05 02:10:00' —log='my-custom-log-name'
 
Specifying start and end times. Note the timestamp format!
$ python3 log-restore.py --compartment=ocid1.compartment.oc1..aaaaaaaappw5e37gjezfrosagy7ja --bucket=logarchive01 --folder=ocid1.serviceconnector.oc1.ca-montreal-1.amaaaaaauwprepboq --start='2019-11-05 02:10:00' --end='2019-11-05 02:10:00'
 
Using shorthand parameter notation
$ python3 log-restore.py -c=ocid1.compartment.oc1..aaaaaaaappw5e37gjezfrosagy7ja -b=logarchive01 -f=ocid1.serviceconnector.oc1.ca-montreal-1.amaaaaaauwprepboq -s='2019-11-05 02:10:00' -e='2019-11-05 02:10:00' -l='my-custom-log-name'
