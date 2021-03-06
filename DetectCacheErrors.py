""" ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------###
Script to check the cache status of a Cache job.

Beginning with: DetectCacheErrors.py
Created on: 11/19/2014
(generated by ArcGIS/ModelBuilder)(arcpy.mapping)

Purpose: To Use the Json of the Cache Job Status in order to determine the 
            the status of the cache and notify administrators if an issue
            has occured.

Authored by: Joe Guzi

Beginning Date: 9/11/2014      Ending Date: 11/19/2014

### ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""


# Import modules
import arcpy, json, time, sys, string, os, traceback, datetime
import smtplib
from email.MIMEText import MIMEText

# Write Log Section
def writelog(logfile,msg):
    try:
        
        f = open(logfile,'a')
        f.write(msg)
        f.close()
    except:
        pass

message = ""
dateTimeStamp = time.strftime('%Y%m%d%H%M%S')
root = os.path.dirname(sys.argv[0]) #"C:\\Users\\jsguzi\\Desktop"
scriptName = sys.argv[0].split("\\")[len(sys.argv[0].split("\\")) - 1][0:-3] #Gets the name of the script without the .py extension  
logFile = root + "\\log\\" + scriptName + "_" + dateTimeStamp[:14] + ".log" #Creates the logFile variable
if os.path.exists(logFile):
    os.remove(logFile)

# Server Connection Variable
servername = "servername"
username = "username" #this must be an arcgis server admin account to access the reporting tools
password = "password"  #you will need to put the admin password here

# Import Geoprocessing Toolbox
toolboxConnection = "http://" + servername + ":6080/arcgis/admin;System/ReportingTools;" + username + ";" + password
arcpy.ImportToolbox(toolboxConnection)

# Using Report CacheStatus_ReportingTools Geoprocessing service to create Json of the Cache status
mapServerName = "mapservicename"
jobSummaryJSON = arcpy.ReportCacheStatus_ReportingTools(mapServerName + ":MapServer", "esriJobSummary", "", "", "", "")

# Cache Status Variables
JSONstring = str(jobSummaryJSON)
PythonJson = json.loads(JSONstring)
AllJobs = PythonJson["jobs"]
LastJob = PythonJson["jobs"][0]
JobID = LastJob["jobId"]
JobStatus = LastJob["jobStatus"]
JobStartTime = LastJob["startTime"]
JobFinishtime = LastJob["lastTime"]
JobStartTimeSeconds = float(JobStartTime)
StartTime = time.ctime(JobStartTimeSeconds)
currentTime = time.time()
CurrentDate = time.ctime(float(currentTime))
DeltaTime = currentTime - JobStartTimeSeconds
DeltaDate = datetime.timedelta(seconds=DeltaTime)

# This checks that the last job occured within the same day that the Script is Currently Running.
# This will ensure that the rebuild cache script is working and that this reporting script is
# reporting on the job that ran in the same day. If the changes in days equals zero the script
# will report on the cache job.
if DeltaDate.days == 0:
    # This checks the status of the most recent job. If it is processing it will enter a while loop
    # where it will wait 5 minutes, recheck the job status, if it is still processing it will 
    # repeat those step until the Status of the Job Changes.
    if JobStatus == "PROCESSING":
        
        while JobStatus == "PROCESSING":
            
            time.sleep(300)

            jobSummaryJSON = arcpy.ReportCacheStatus_ReportingTools(mapServerName + ":MapServer", "esriJobSummary", "", "", "", "")
            JSONstring = str(jobSummaryJSON)
            PythonJson = json.loads(JSONstring)
            LastJob = PythonJson["jobs"][0]
            JobID = LastJob["jobId"]
            JobStatus = LastJob["jobStatus"]
    # This checks the Status of the most recent job. If the Job Status is cancelled, the script will
    # send an email to notify administrators to investigate the reason the cache was cancelled and 
    # whether or not any thing needs to be done to finish building the cache. 
    elif JobStatus == "CANCELED":
        # Send Email
        message += str(JobID) + "\n"
        message += JobStatus + "\n"
        message += "Job Cancelled?" + "\n"
        message += "Start Time: "+ StartTime + "\n"
        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
        formatted_lines = traceback.format_exc().splitlines()
        writelog(logFile,message + "\n" + formatted_lines[-1])
        #sys.exit(1) this is where the sys.exit command was originally. i moved it to the end to ensure it will send the email before exiting 
    
        # This is the email notification piece [%]
        #email error notification
        smtpserver = 'mailrelay.co.stark.oh.us'
        AUTHREQUIRED = 0 # if you need to use SMTP AUTH set to 1
        smtpuser = ''  # for SMTP AUTH, set SMTP username here
        smtppass = ''  # for SMTP AUTH, set SMTP password here

        RECIPIENTS = ['jsguzi@starkcountyohio.gov', 'bwhall@starkcountyohio.gov']
        SENDER = 'webags@starkcountyohio.gov'
        #msg = arcpy.GetMessages()***I think I need to look at the message variable
        #msg = arcpy.GetMessage(0)# Brian Corrected this it is arcpy.GetMessage()
        #msg += arcpy.GetMessage(2)# Brian Corrected this it is arcpy.GetMessage()
        #msg += arcpy.GetMessage(3)# Brian Corrected this it is arcpy.GetMessage()
        msg = MIMEText(message) #***i pointed this mime thing at the message 
        msg['Subject'] = 'Cache Job Cancelled. Look into this'
        # Following headers are useful to show the email correctly
        # in your recipient's email box, and to avoid being marked
        # as spam. They are NOT essential to the sendmail call later
        msg['From'] = "ArcGIS on WebAGS "
        msg['Reply-to'] = "Joe Guzi "
        msg['To'] = "jsguzi@starkcountyohio.gov"

        session = smtplib.SMTP(smtpserver)
        if AUTHREQUIRED:
            session.login(smtpuser, smtppass)
        session.sendmail(SENDER, RECIPIENTS, msg.as_string())
        session.close()

    # This checks the Status of the most recent job. If the Job Status is Done, the script will
    # just write the log into the log folder. This indicated that the cache job was successful.
    elif JobStatus == "DONE":
        message += str(JobID) + "\n"
        message += JobStatus + "\n"
        message += "Job Completed!" + "\n"
        message += "Start Time :"+ StartTime + "\n"
        writelog(logFile,message + "\n")

    # This checks the Status of the most recent job. If the Job Status is Partial Error, the script will
    # send an email to notify administrators to investigate the reason the cache encountered an error, 
    #  it will also dig in and indicate which levels contain errors, and whether or not any thing needs
    # to be done to finish building the cache.
    elif JobStatus == "PARTIALERROR":
        message += str(JobID) + "\n"
        message += JobStatus + "\n"
        message += "Job Has Encountered an Error" + "\n"
        message += "Start Time :"+ StartTime + "\n"
        # Dig deeper
        levelInfo = LastJob["lodInfos"]
        for levelstatus in levelInfo:
            levelID = levelstatus["levelID"]
            LODstatus = levelstatus["status"]
            message += str(levelID) + "\n"
            message += LODstatus + "\n"

        # Send Email
        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
        formatted_lines = traceback.format_exc().splitlines()
        writelog(logFile,message + "\n" + formatted_lines[-1])
        #sys.exit(1) this is where the sys.exit command was originally. i moved it to the end to ensure it will send the email before exiting 
    
        # This is the email notification piece [%]
        #email error notification
        smtpserver = 'mailrelay.co.stark.oh.us'
        AUTHREQUIRED = 0 # if you need to use SMTP AUTH set to 1
        smtpuser = ''  # for SMTP AUTH, set SMTP username here
        smtppass = ''  # for SMTP AUTH, set SMTP password here

        RECIPIENTS = ['jsguzi@starkcountyohio.gov', 'bwhall@starkcountyohio.gov']
        SENDER = 'webags@starkcountyohio.gov'
        #msg = arcpy.GetMessages()***I think I need to look at the message variable
        #msg = arcpy.GetMessage(0)# Brian Corrected this it is arcpy.GetMessage()
        #msg += arcpy.GetMessage(2)# Brian Corrected this it is arcpy.GetMessage()
        #msg += arcpy.GetMessage(3)# Brian Corrected this it is arcpy.GetMessage()
        msg = MIMEText(message) #***i pointed this mime thing at the message 
        msg['Subject'] = 'Cache Job Has Encountered An Error. Look into this'
        # Following headers are useful to show the email correctly
        # in your recipient's email box, and to avoid being marked
        # as spam. They are NOT essential to the sendmail call later
        msg['From'] = "ArcGIS on WebAGS "
        msg['Reply-to'] = "Joe Guzi "
        msg['To'] = "jsguzi@starkcountyohio.gov"

        session = smtplib.SMTP(smtpserver)
        if AUTHREQUIRED:
            session.login(smtpuser, smtppass)
        session.sendmail(SENDER, RECIPIENTS, msg.as_string())
        session.close()
# If the job was not run the same day this script was run, then this script
# will send an email to administrators so that they might be able to determine
# if there was a reason for the Cache not to be updated.
else:
    # Send Email
    message += "Job has not run in: " + DeltaDate.days + "\n"
    message += JobStatus + "\n"
    message += "Last Job:" + str(JobID) + "\n"
    message += "Start Time: "+ StartTime + "\n"
    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
    formatted_lines = traceback.format_exc().splitlines()
    writelog(logFile,message + "\n" + formatted_lines[-1])
    #sys.exit(1) this is where the sys.exit command was originally. i moved it to the end to ensure it will send the email before exiting 
    
    # This is the email notification piece [%]
    #email error notification
    smtpserver = 'mailrelay.co.stark.oh.us'
    AUTHREQUIRED = 0 # if you need to use SMTP AUTH set to 1
    smtpuser = ''  # for SMTP AUTH, set SMTP username here
    smtppass = ''  # for SMTP AUTH, set SMTP password here

    RECIPIENTS = ['jsguzi@starkcountyohio.gov', 'bwhall@starkcountyohio.gov']
    SENDER = 'webags@starkcountyohio.gov'
    #msg = arcpy.GetMessages()***I think I need to look at the message variable
    #msg = arcpy.GetMessage(0)# Brian Corrected this it is arcpy.GetMessage()
    #msg += arcpy.GetMessage(2)# Brian Corrected this it is arcpy.GetMessage()
    #msg += arcpy.GetMessage(3)# Brian Corrected this it is arcpy.GetMessage()
    msg = MIMEText(message) #***i pointed this mime thing at the message 
    msg['Subject'] = 'Cache job did not run. Look into this...'
    # Following headers are useful to show the email correctly
    # in your recipient's email box, and to avoid being marked
    # as spam. They are NOT essential to the sendmail call later
    msg['From'] = "ArcGIS on WebAGS "
    msg['Reply-to'] = "Joe Guzi "
    msg['To'] = "jsguzi@starkcountyohio.gov"

    session = smtplib.SMTP(smtpserver)
    if AUTHREQUIRED:
        session.login(smtpuser, smtppass)
    session.sendmail(SENDER, RECIPIENTS, msg.as_string())
    session.close()
