#!/usr/bin/python3
#
#  NAME
#   Log-Restore.py
#
#  DESCRIPTION
#   Restore archived logs to the OCI Logging Service
#
#  MODIFIED  (MM/DD/YY)
#  rbarnes   10/10/21 - Creation
#


import oci 
import os
import argparse
from datetime import datetime, timedelta
import pytz
import json
import gzip

parser = argparse.ArgumentParser()
parser.add_argument('--compartment', '-c', help="Compartment_OCID [Required]", type= str)
parser.add_argument('--bucket', '-b', help="Object Storage Bucket [Required]", type= str)
parser.add_argument('--folder', '-f', help="Object Storage Folder [Required]", type= str)
parser.add_argument('--start', '-s', help="Start time for log source [Optional]", type= str, default = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"))
parser.add_argument('--end', '-e', help="End time for log source [Optional]", type= str, default = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"))
parser.add_argument('--logname', '-l', help="Imported log name [Optional]", type= str, default= "archive-restore-log")

args = parser.parse_args()

_compartment_id = args.compartment
_bucket = args.bucket 
_folder = args.folder 
_startdtm = pytz.utc.localize((datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S') + timedelta(hours=-24)))
_enddtm = pytz.utc.localize(datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S'))
_logname = args.logname 
_region = os.environ.get('OCI_REGION')

"""
Identify and enumerate archive log objects
"""
def findArchiveLogObjects(_object_storage_client, _namespace):
    try:
        get_bucket_response = _object_storage_client.get_bucket(
            namespace_name=_namespace,
            bucket_name=_bucket
        )
        list_objects_response = _object_storage_client.list_objects(
            namespace_name=_namespace,
            bucket_name=_bucket,
            prefix=_folder,
            limit=1000,
            fields="timeCreated"
        )
        all_objects = list_objects_response.data.objects

        target_list = []

        for object in all_objects:
            if ((object.time_created > _startdtm) and (object.time_created < _enddtm)):
                target_list.append(object.name)
        return target_list
    except Exception as err:
        print("An exception occured in findArchiveLogObjects()")
        raise(err)
"""
Verify exists, or create if needed, Log Group and return OCID
"""
def prepLogGroup(_logging_client):
    try:
        list_log_groups_response = _logging_client.list_log_groups(
            compartment_id=_compartment_id,
            display_name="Archive_Restore_Log_Grp")
        if (list_log_groups_response.data):
            return list_log_groups_response.data[0].id
        else:
            print("Creating log group Archive_Restore_Log_Grp...")
            print("")
            create_log_group_response = _logging_client.create_log_group(
                create_log_group_details=oci.logging.models.CreateLogGroupDetails(
                    compartment_id=_compartment_id,
                    display_name="Archive_Restore_Log_Grp",
                    description="Log group for ingesting archived logs"
                )
            )
            list_log_groups_response = _logging_client.list_log_groups(
                compartment_id=_compartment_id,
                display_name="Archive_Restore_Log_Grp")
            if (list_log_groups_response.data):
                return list_log_groups_response.data[0].id
    except Exception as err:
        print("An exception occured in prepLogGroup()")
        raise(err)

"""
Verify exists, or create if needed, and return OCID
"""
def prepRestoreLog(_logging_client, _logGrpOCID, _logname):
    try:
        list_logs_response = _logging_client.list_logs(
            log_group_id=_logGrpOCID,
            log_type="CUSTOM",
            display_name=_logname)
        if (list_logs_response.data):
            return list_logs_response.data[0].id
        else:
            print("Creating archive restore log: {}".format(_logname))
            print("")
            create_log_response = _logging_client.create_log(
                log_group_id=_logGrpOCID,
                create_log_details=oci.logging.models.CreateLogDetails(
                    display_name=_logname,
                    log_type="CUSTOM")
            )
            list_logs_response = _logging_client.list_logs(
                log_group_id=_logGrpOCID,
                log_type="CUSTOM",
                display_name=_logname)
            if (list_logs_response.data):
                return list_logs_response.data[0].id
    except Exception as err:
        print("An exception occured in prepRestoreLog()")
        raise(err)

"""
Restore archive logs to Logging service
"""
def restoreLogs(_object_storage_client,  _namespace, _bucket, _loggingingestion_client, _logOCID, archive_log_list, _folder):
    try:
        if not(os.path.exists(_folder)):
            os.makedirs(_folder)

        for logObjectName in archive_log_list:
            print(logObjectName)

            if (os.path.exists(logObjectName)):
                os.remove(logObjectName)            

            get_obj = _object_storage_client.get_object(
                namespace_name=_namespace,
                bucket_name=_bucket,
                object_name=logObjectName
            )

            with open(logObjectName,'wb') as f:
                for chunk in get_obj.data.raw.stream(1024 * 1024, decode_content=False):
                    f.write(chunk)

            with gzip.open(logObjectName, 'rb') as file:
                log_entries_str = file.readlines()

            length_of_list = len(log_entries_str)
            _log_entries = []

            for i in range(length_of_list):
                log_entry_json = json.loads(log_entries_str[i])
                log_entry = {
                    "data" : (json.dumps(log_entry_json['data'])).replace("{","").replace("}","").replace("\\","").replace('"',""),
                    "id" : log_entry_json['id'],
                    "time" : log_entry_json['time']
                }

                _log_entries.append(log_entry)

            if (os.path.exists(logObjectName)):
                os.remove(logObjectName)    

            logEntryBatches = []

            logEntryBatch = oci.loggingingestion.models.LogEntryBatch(
                entries=_log_entries,
                source="Log-Restore",
                type="Log-Restore",
                defaultlogentrytime=datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S.%f")[:-3]+"Z",
                subject="Log_Content_Restore_Staging_Area"
            ) 

            logEntryBatches.append(logEntryBatch)

            put_log_response = _loggingingestion_client.put_logs(
                log_id=_logOCID,
                put_logs_details=oci.loggingingestion.models.PutLogsDetails(
                    log_entry_batches=logEntryBatches,
                    specversion="1.0"
                )   
            ) 
    except Exception as err: 
        print("There was an exception in executing restoreLogs()") 
        raise(err) 

"""
Main process
"""
def main():
    try:
        config = oci.config.from_file()
        config['region']=_region
    
        object_storage_client = oci.object_storage.ObjectStorageClient(config)
        logging_client = oci.logging.LoggingManagementClient(config)
        loggingingestion_client = oci.loggingingestion.LoggingClient(config)
    
        get_namespace_response = object_storage_client.get_namespace(compartment_id=_compartment_id)
        _namespace = get_namespace_response.data

        archive_log_list = findArchiveLogObjects(object_storage_client, _namespace)

        if len(archive_log_list):
            _logGrpOCID = prepLogGroup(logging_client)
            _logOCID = prepRestoreLog(logging_client, _logGrpOCID, _logname)
            print("")
            print("Restoring archive logs....")
            restoreLogs(object_storage_client, _namespace, _bucket, loggingingestion_client, _logOCID, archive_log_list, _folder)
            print("")
            print("Completed processing archive log(s)....")
            print("")
        else:    
	        print('There are no matching log archive files for the time period requested')
    except Exception as err:
        print("There was a problem with executing this restore process.  Error message:")
        print(err)

"""
Script entrypoint
"""
main()


