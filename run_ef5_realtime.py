"""
Generic FLASH real-time model/subdomain execution script
by Jorge A. Duarte G. - jorge.duarte@noaa.gov
V.1.0 - March 20, 2020

This script consolidates the FLASH execution routines in a single script, while
ingesting a "configuration file" from where a given model can be specified for a
given domain. Please use this script and a configuration file as follows:

    $> python run_realtime_oCONUS.py <configuration_file.py>

Said configuration file should contain the each of its variables populated, as can be
seen in the following example configuration file contents:

domain = "NEVERLAND"
subdomain = "NVRailways"
systemModel = "crest"
systemName = systemModel.upper() + " " + domain.upper() + " " + subdomain.upper()
ef5Path = "/run/EF5/bin/ef5"
statesPath = "/run/states/"
precipFolder = "/run/precip/"
modelStates = ["crest_SM", "kwr_IR", "kwr_pCQ", "kwr_pOQ"]
templatePath = "/run/templates/"
templates = ["ef5_template.txt"]
DATA_ASSIMILATION = False
assimilationPath = ""
assimilationLogs = []
dataPath = "/run/outputs"
tmpOutput = dataPath + "tmp_output_" + systemModel + "/"
SEND_ALERTS = True
smtp_server = "smtp.gmail.com"
smtp_port = 587
account_address = "model_alerts@gmail.com"
account_password = "supersecurepassword9000"
alert_sender = "Real Time Model Alert" # can also be the same as account_address
alert_recipients = ["fixer1@company.com", "fixer2@company.com", "panic@company.com",...]
"""

from shutil import rmtree, copy
from os import makedirs, listdir, rename, remove
import glob
from datetime import datetime as dt
from datetime import timedelta
import errno
import datetime
import time
import numpy as np
import re
import subprocess
import threading
import sys
import socket
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from multiprocessing.pool import ThreadPool
from swissmeteo_mod import Swissmeteo


"""
Setup Environment Variables for Linux Shared Libraries and OpenMP Threads
"""
os.environ['LD_LIBRARY_PATH'] = '/usr/local/lib'
os.environ['OMP_NUM_THREADS'] = '1'

def main(args):
    """Main function of the script.

    This function reads the real-time configuration script, makes sure the necessary files to run
    FLASH exist and are in the right place, runs the model(s), writes the outputs and states, and
    reports vie email if an error occurs during execution.

    Arguments:
        args {list} -- the first argument ([1]) corresponds to a real-time configuration file.
    """

    # Read the configuration file
    #config_file = __import__(args[1].replace('.py', ''))
    import CREST_SWITZERLAND_CONFIG as config_file #Harcoded here since there is a problem importing the file given its full path
    domain = config_file.domain
    subdomain = config_file.subdomain
    systemModel = config_file.systemModel
    systemName = config_file.systemName
    ef5Path = config_file.ef5Path
    precipArchive = config_file.precipArchive
    precipFolder = config_file.precipFolder
    statesPathSub01 = config_file.statesPathSub01
    statesPathSub02 = config_file.statesPathSub02
    modelStates = config_file.modelStates
    templatePath = config_file.templatePath
    templateSub01 = config_file.templateSub01
    templateSub02 = config_file.templateSub02
    DATA_ASSIMILATION = config_file.DATA_ASSIMILATION
    assimilationPath = config_file.assimilationPath
    assimilationLogs = config_file.assimilationLogs
    dataPath = config_file.dataPath
    tmpOutputSub01 = config_file.tmpOutputSub01
    tmpOutputSub02 = config_file.tmpOutputSub02
    SEND_ALERTS = config_file.SEND_ALERTS
    smtp_server = config_file.smtp_server
    smtp_port = config_file.smtp_port
    account_address = config_file.account_address
    account_password = config_file.account_password
    alert_sender = config_file.alert_sender
    alert_recipients = config_file.alert_recipients
    MODEL_RES = config_file.model_resolution
    SampleTIFF = config_file.sample_geotiff
    product_Path = config_file.product_Path
    geoFile = "/home/ec2-user/Scripts/post_processing/georef_file.txt"
    thread_th = config_file.thread_th
    distance_th = config_file.distance_th
    Npixels_th = config_file.Npixels_th


    # Figure out the timing for running the current timestep
    currentTime = dt.utcnow()

    print("*** Starting real-time run cycle at " + currentTime.strftime("%Y%m%d_%H%M") + " ***")

    # Round down the current minutess to the nearest 10min increment in the past
    min10 = int(np.floor(currentTime.minute / 10.0) * 10)
    # Use the rounded down minutes as the timestamp for the current time step
    currentTime = currentTime.replace(minute=min10,second=0,microsecond=0)

    # If Get a lock on the current thread
    if not get_lock(systemModel+domain.lower()+subdomain.lower()):
        subject = systemName + ' failed for ' + currentTime.strftime("%Y%m%d_%H%M")
        message = 'Could not acquire lock'
        for recipient in alert_recipients:
            send_mail(smtp_server, smtp_port, account_address, account_password, alert_sender, recipient, subject, message)
        sys.exit()

    # Configure the system to run once every hour
    # Start the simulation using QPEs from 60min ago
    systemStartTime = currentTime - timedelta(minutes=60)
    # Save states for the current run with the current time step's timestamp
    systemStateEndTime = currentTime
    # Run warm up using the last hour of data until the current time step
    systemWarmEndTime = currentTime
    # Setup the simulation forecast starting point as the current timestemp
    systemStartLRTime = currentTime
    # Run simulation for 360min (6 hours) into the future using the 72 QPFs (5minx72=6h)
    systemEndTime = currentTime + timedelta(minutes=360)

    # Configure failure-tolerance for missing QPE timesteps
    # Only check for states as far as we have QPFs (6 hours)
    failTime = currentTime - timedelta(hours=6)


    try:
        # Clean up old QPE files from GeoTIFF archive (older than 6 hours)
        #      Keep latest QPFs
        cleanup_precip(currentTime, failTime, precipFolder)

        # Get the necessary QPEs and QPFs for the current time step into the GeoTIFF precip folder
        # store whether there's a QPE gap or the QPEs for the current time step is missing
        ahead, gap, exists = get_new_precip(currentTime, precipArchive, precipFolder)

        # If not possible to get precip data ABORT!
        if(ahead == None or gap == None or exists == None):
            print("ABORTING: Could not get precip data from NetCDF feed!!!")
            if SEND_ALERTS:
                subject = systemName + ' failed to get precip for ' + currentTime.strftime("%Y%m%d_%H%M")
                message = 'Could not get rainfall for ' + systemStartTime.strftime("%Y%m%d_%H%M")
                for recipient in alert_recipients:
                    send_mail(smtp_server, smtp_port, account_address, account_password, alert_sender, recipient, subject, message)
            sys.exit(1)
        # If there was a QPE gap:
        elif(exists and gap):
                #TODO: find the QPE gap in the GeoTIFF folder, and use QPFs to fill it
                fill_gap(currentTime, precipFolder)

    except:
        print("There was a problem with the QPE routines. Ignoring errors and continuing with execution")

    # Check to see if all the states for the current time step are available: ["crest_SM", "kwr_IR", "kwr_pCQ", "kwr_pOQ"]
    # If not then search for previous ones
    foundAllStatesSub01 = False
    foundAllStatesSub02 = False
    realSystemStartTime = systemStartTime

    # Iterate over all necessary states and check if they're available for the current run
    # Only go back up to 6 hours, in 10min decrements
    while foundAllStatesSub01 == False and realSystemStartTime > failTime:
        foundAllStatesSub01 = True
        for state in modelStates:
            if is_non_zero_file(statesPathSub01 + state + "_" + realSystemStartTime.strftime("%Y%m%d_%H%M") + ".tif") == False:
                print('Missing start state: ' + statesPathSub01 + state + '_' + realSystemStartTime.strftime("%Y%m%d_%H%M") + '.tif')
                foundAllStatesSub01 = False
        if foundAllStatesSub01 == False:
            realSystemStartTime = realSystemStartTime - timedelta(minutes=10)

    while foundAllStatesSub02 == False and realSystemStartTime > failTime:
        foundAllStatesSub02 = True
        for state in modelStates:
            if is_non_zero_file(statesPathSub02 + state + "_" + realSystemStartTime.strftime("%Y%m%d_%H%M") + ".tif") == False:
                print('Missing start state: ' + statesPathSub02 + state + '_' + realSystemStartTime.strftime("%Y%m%d_%H%M") + '.tif')
                foundAllStatesSub02 = False
        if foundAllStatesSub02 == False:
            realSystemStartTime = realSystemStartTime - timedelta(minutes=10)

    # If no states are found for the last 6 hours, assume that no previous states exist, and
    # use the current time step as the starting point for a "cold" start.
    # If notifications are enabled, notify all recipients about not finding states.
    if not foundAllStatesSub01 or not foundAllStatesSub02:
        if SEND_ALERTS:
            subject = systemName + ' failed for ' + currentTime.strftime("%Y%m%d_%H%M")
            message = 'Missing states from ' + realSystemStartTime.strftime("%Y%m%d_%H%M") + ' to ' + systemStartTime.strftime("%Y%m%d_%H%M") + '. Starting model with cold states.'
            for recipient in alert_recipients:
                send_mail(smtp_server, smtp_port, account_address, account_password, alert_sender, recipient, subject, message)
        print('No states found!!!')
        realSystemStartTime = systemStartTime
    # If notifications are enabled, notify if no immediately anteceding states existed,
    # and had to use old states.
    elif realSystemStartTime != systemStartTime:
        if SEND_ALERTS:
            subject = systemName + ' warning for ' + currentTime.strftime("%Y%m%d_%H%M")
            message = 'Using states from ' + realSystemStartTime.strftime("%Y%m%d_%H%M") + ' instead of ' + systemStartTime.strftime("%Y%m%d_%H%M")
            for recipient in alert_recipients:
               send_mail(smtp_server, smtp_port, account_address, account_password, alert_sender, recipient, subject, message)
        print('Had to use older states')

    print("Running simulation system for: " + currentTime.strftime("%Y%m%d_%H%M"))
    print("Simulations start at: " + realSystemStartTime.strftime("%Y%m%d_%H%M") + " and ends at: " + systemEndTime.strftime("%Y%m%d_%H%M") + " while state update ends at: " + systemStateEndTime.strftime("%Y%m%d_%H%M"))

    # Clean up "Hot" folders
    # Delete the previously existing "Hot" folders, ignore error if it doesn't exist
    rmtree(tmpOutputSub01, ignore_errors=1)
    rmtree(tmpOutputSub02, ignore_errors=1)
    rmtree(dataPath, ignore_errors=1)
    # Create the "Hot" folder for the current run
    mkdir_p(tmpOutputSub01)
    mkdir_p(tmpOutputSub02)
    mkdir_p(dataPath)

    # Create the control files for both subdomains
    # Define the control file path to create
    controlFileSub01 = tmpOutputSub01 + "flash_" + subdomain + "_" + systemModel + "_sub01.txt"
    fOut = open(controlFileSub01, "w")

    # Create a control file with updated fields
    for line in open(templatePath + templateSub01).readlines():
        line = re.sub('{OUTPUTPATH}', tmpOutputSub01, line)
        line = re.sub('{TIMEBEGIN}', realSystemStartTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{TIMEBEGINLR}', systemStartLRTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{TIMEWARMEND}', systemWarmEndTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{TIMESTATE}', systemStateEndTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{TIMEEND}', systemEndTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{SYSTEMMODEL}', systemModel, line)
        fOut.write(line)
    fOut.close()

    # If data assimilation if being used for CREST, clean up previous data assimilation logs
    #TODO: Verify against EF5 control file - when this functionality is needed
    if DATA_ASSIMILATION and systemModel=="crest":
        # Data assimilation output files
        for log in assimilationLogs:
            if is_non_zero_file(assimilationPath + log) == True:
                remove(assimilationPath + log)

    # Define each control file path to create
    controlFileSub02 = tmpOutputSub02 + "flash_" + subdomain + "_" + systemModel + "_sub02.txt"
    fOut = open(controlFileSub02, "w")

    # Create a control file with updated fields from each template
    for line in open(templatePath + templateSub02).readlines():
        line = re.sub('{OUTPUTPATH}', tmpOutputSub02, line)
        line = re.sub('{TIMEBEGIN}', realSystemStartTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{TIMEBEGINLR}', systemStartLRTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{TIMEWARMEND}', systemWarmEndTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{TIMESTATE}', systemStateEndTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{TIMEEND}', systemEndTime.strftime('%Y%m%d%H%M'), line)
        line = re.sub('{SYSTEMMODEL}', systemModel, line)
        fOut.write(line)
    fOut.close()

    # If data assimilation if being used for CREST, clean up previous data assimilation logs
    #TODO: Verify against EF5 control file - when this functionality is needed
    if DATA_ASSIMILATION and systemModel=="crest":
        # Data assimilation output files
        for log in assimilationLogs:
            if is_non_zero_file(assimilationPath + log) == True:
                remove(assimilationPath + log)


    # Run EF5 simulations
    # Prepare function arguments for multiprocess invovation of run_EF5()
    argumentsSub01 = [ef5Path, tmpOutputSub01, controlFileSub01, "ef5_sub01.log"]
    argumentsSub02 = [ef5Path, tmpOutputSub02, controlFileSub02, "ef5_sub02.log"]

    # Create a thread pool of the same size as the number of control files
    tp = ThreadPool(2)
    # Run each EF5 instance asynchronously using independent threads
    tp.apply_async(run_EF5, argumentsSub01)
    tp.apply_async(run_EF5, argumentsSub02)

    # Wait for both processes to finish and collapse the thread pool
    tp.close()
    tp.join()

    # Merge all partial outputs into a single geotiff and write them out into the dataPath
    # gdal_merge.py -a_nodata -9999 -co COMPRESS=Deflate -o OUTPUTFILE.tif SUB01_FILE.tif SUB02_FILE.tif
    #partial_files_sub01 = os.listdir(tmpOutputSub01)
    #partial_files_sub02 = os.listdir(tmpOutputSub02)

    #for file1, file2 in zip(partial_files_sub01, partial_files_sub02):
    #    if file1 == file2 and file1 != "results.json" and file1 != "ef5_sub01.log":
    #        subprocess.call("/home/ec2-user/anaconda3/bin/gdal_merge.py -a_nodata -9999 -co COMPRESS=Deflate -o " + dataPath + file1 + " " + tmpOutputSub01 + file1 + " " + tmpOutputSub02 + file2, shell=True)

    # Merge all partial outputs into a single geotiff and write them out into the dataPath
    tp = ThreadPool(10)

    subdomain_list_of_folders = [tmpOutputSub01, tmpOutputSub02]

    #First merge forecast integrated files
    fcst_integrated_files = ["maxunitq." + systemWarmEndTime.strftime('%Y%m%d.%H%M') + "00.tif", "qpfaccum." + systemWarmEndTime.strftime('%Y%m%d.%H%M') + "00.tif", "qpeaccum." + systemWarmEndTime.strftime('%Y%m%d.%H%M') + "00.tif", "maxq." + systemWarmEndTime.strftime('%Y%m%d.%H%M') + "00.tif"]
    for fcst_file in fcst_integrated_files:
        argumentsPacket = [dataPath, subdomain_list_of_folders, fcst_file]

        #Send argument list for processing
        tp.apply_async(merge_EF5, argumentsPacket)

    #Now merge each Q grid at every time step
    forecastTime = systemStartLRTime
    while forecastTime <= systemEndTime:
        current_q_file = "q." + forecastTime.strftime('%Y%m%d_%H%M') + ".crest.tif"

        argumentsPacket = [dataPath, subdomain_list_of_folders, current_q_file]

        #Send argument list for processing
        tp.apply_async(merge_EF5, argumentsPacket)

        #Advance forecastTime variable by 5 minutes
        forecastTime = forecastTime + timedelta(minutes=5)

    # Wait for both processes to finish and collapse the thread pool
    tp.close()
    tp.join()

    #Post-Processing: Computing probability of an impact over RhB Track
    # Create a thread pool of the same size as the number of control files
    tp = ThreadPool(10)
    forecastTime = systemStartLRTime
    while forecastTime <= systemEndTime:
        #Prepare package to pass to every worker
        current_q_forecast = dataPath + "q." + forecastTime.strftime('%Y%m%d_%H%M') + ".crest.tif"

        #Name of probability CSV file
        output_rhbti_forecast = dataPath + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + forecastTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-RHBTIPROBABILITY-" + MODEL_RES + "-GRAUBUNDEN.csv.gz"
        #Name of unit Q CSV file
        unitq_name = dataPath + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + forecastTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-UNITQ-" + MODEL_RES + "-GRAUBUNDEN.csv.gz"

        #Prepare arguments to pass
        argumentsPacket = [current_q_forecast, dataPath, output_rhbti_forecast, unitq_name]

        #Send argument list for processing
        tp.apply_async(postprocess_EF5, argumentsPacket)

        #Advance forecastTime variable by 5 minutes
        forecastTime = forecastTime + timedelta(minutes=5)

    # Wait for both processes to finish and collapse the thread pool
    tp.close()
    tp.join()

    # Move product files to permanent storage
    product_file_list = glob.glob(dataPath + "*.csv.gz")

    for prod_file in product_file_list:
        subprocess.call("/usr/bin/cp " + prod_file + " " + product_Path, shell=True)

    # Additional processing for web-display
    # Convert CSV probability file to GeoTIFF
    subprocess.call("/home/ec2-user/anaconda3/bin/python /home/ec2-user/Scripts/post_processing/GenForecastTIFF.py " + product_Path + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-RHBTIPROBABILITY-" + MODEL_RES + "-GRAUBUNDEN.csv.gz " + dataPath + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-RHBTI-" + MODEL_RES + ".tif " + SampleTIFF, shell=True)

    # Compute probability for Max Q
    #Prepare package to pass to every worker
    maxq_forecast = dataPath + "maxq." + systemStartLRTime.strftime('%Y%m%d.%H%M') + "00.tif"
    #Name of probability CSV file
    output_maxq_rhbti_forecast = dataPath + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-MAXRHBTIPROBABILITY-" + MODEL_RES + "-GRAUBUNDEN.csv.gz"
    #Name of unit Q CSV file
    dummy_unitq_name = dataPath + "CRESTMETSWISS-MAXUNITQ.csv.gz"
    #Post-process Max Q
    postprocess_EF5(maxq_forecast, dataPath, output_maxq_rhbti_forecast, dummy_unitq_name)
    # Convert CSV probability file to GeoTIFF
    subprocess.call("/home/ec2-user/anaconda3/bin/python /home/ec2-user/Scripts/post_processing/GenForecastTIFF.py " + output_maxq_rhbti_forecast + " " + dataPath + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-MAXQRHBTI-" + MODEL_RES + ".tif " + SampleTIFF, shell=True)
    # Derive Threat Polygons from MAXQRHBTI GeoTIFF
    sp.call("/home/ec2-user/anaconda3/bin/python /home/ec2-user/Scripts/post_processing/createEventObjects.py " + dataPath + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-MAXQRHBTI-" + MODEL_RES + ".tif " + str(thread_th) + " " + str(distance_th) + " " + str(Npixels_th) + " " + output_file + " " + geoFile + " shp", shell=True)
    #kml_output_file = csv_folder + "joint." + dateStamp.strftime('%Y%m%d.%H%M') + "00.kml"
    #sp.call('ogr2ogr -f KML ' + output_file + ' ' + input_file + ' -dialect sqlite -sql "select ST_union(Geometry) from ' + var_name + '"', shell=True)

    # Move GeoTIFFs to permanent storage for web-display
    copyToWeb = True
    if copyToWeb == True:
        #Copy maxunitq file to permanent folder
        subprocess.call("/usr/bin/cp " + dataPath + "maxunitq." + systemWarmEndTime.strftime('%Y%m%d.%H%M') + "00.tif " + product_Path + currentTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-MAXUNITSTREAMFLOW-" + MODEL_RES + ".tif", shell=True)
        #Copy qpfaccum file to permanent folder
        subprocess.call("/usr/bin/cp " + dataPath + "qpfaccum." + systemWarmEndTime.strftime('%Y%m%d.%H%M') + "00.tif " + product_Path + currentTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-QPFACCUM-" + MODEL_RES + ".tif", shell=True)
        #Copy qpeaccum file to permanent folder
        subprocess.call("/usr/bin/cp " + dataPath + "qpeaccum." + systemWarmEndTime.strftime('%Y%m%d.%H%M') + "00.tif " + product_Path + currentTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-QPEACCUM-" + MODEL_RES + ".tif", shell=True)
        #Copy maxq file to permanent folder
        subprocess.call("/usr/bin/cp " + dataPath + "maxq." + systemWarmEndTime.strftime('%Y%m%d.%H%M') + "00.tif " + product_Path + currentTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-MAXSTREAMFLOW-" + MODEL_RES + ".tif", shell=True)
        #Copy maxq RhbTI probability file to permanent folder
        subprocess.call("/usr/bin/cp " + dataPath + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-MAXQRHBTI-" + MODEL_RES + ".tif " + product_Path, shell=True)
        #Copy RhbTI probability file at analysis time
        subprocess.call("/usr/bin/cp " + dataPath + systemStartLRTime.strftime('%H%M00-%Y%m%d-') + "CRESTMETSWISS-RHBTI-" + MODEL_RES + ".tif " + product_Path, shell=True)

    # Check for missing states if ef5 crashed/did not run
    foundAllStatesSub01 = True
    for state in modelStates:
        if is_non_zero_file(statesPathSub01 + state + "_" + systemStateEndTime.strftime("%Y%m%d_%H%M") + ".tif") == False:
            print('Missing state: ' + statesPathSub01 + state + '_' + systemStateEndTime.strftime("%Y%m%d_%H%M") + '.tif')
            if foundAllStatesSub01 == True:
                foundAllStatesSub01 = False
                if SEND_ALERTS:
                    subject = systemName + ' failed for ' + currentTime.strftime("%Y%m%d_%H%M")
                    message = 'Missing state: ' + statesPathSub01 + state + "_" + systemStateEndTime.strftime("%Y%m%d_%H%M") + ".tif"
                    for recipient in alert_recipients:
                        send_mail(smtp_server, smtp_port, account_address, account_password, alert_sender, recipient, subject, message)

    # Only delete previous states if we have all the current ones
    if foundAllStatesSub01 == True:
        for state in modelStates:
            remove(statesPathSub01 + state + "_" + realSystemStartTime.strftime("%Y%m%d_%H%M") + ".tif")

    foundAllStatesSub02 = True
    for state in modelStates:
        if is_non_zero_file(statesPathSub02 + state + "_" + systemStateEndTime.strftime("%Y%m%d_%H%M") + ".tif") == False:
            print('Missing state: ' + statesPathSub02 + state + '_' + systemStateEndTime.strftime("%Y%m%d_%H%M") + '.tif')
            if foundAllStatesSub02 == True:
                foundAllStatesSub02 = False
                if SEND_ALERTS:
                    subject = systemName + ' failed for ' + currentTime.strftime("%Y%m%d_%H%M")
                    message = 'Missing state: ' + statesPathSub02 + state + "_" + systemStateEndTime.strftime("%Y%m%d_%H%M") + ".tif"
                    for recipient in alert_recipients:
                        send_mail(smtp_server, smtp_port, account_address, account_password, alert_sender, recipient, subject, message)

    # Only delete previous states if we have all the current ones
    if foundAllStatesSub02 == True:
        for state in modelStates:
            remove(statesPathSub02 + state + "_" + realSystemStartTime.strftime("%Y%m%d_%H%M") + ".tif")

    finishTime = dt.utcnow()
    print("*** At " + finishTime.strftime("%Y%m%d_%H%M") + ": Successfully completed real-time run cycle started at " + currentTime.strftime("%Y%m%d_%H%M") + " ***")

def mkdir_p(path):
    """Function that makes a new directory.

    This function tries to make directories, ignoring errors if they exist.

    Arguments:
        path {str} -- path of folder to create
    """
    try:
        makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

def is_non_zero_file(fpath):
    """Function that checks if a file exists and is not empty

    Arguments:
        fpath {str} -- file path to check

    Returns:
        bool -- True or False
    """
    if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
        return True
    else:
        return False


def send_mail(smtp_server, smtp_port, account_address, account_password, sender, to, subject, text):
    """Function to send error emails

    Arguments:
        to {str} -- destination email address
        subject {str} -- email subject
        text {str} -- email message contents
    """
    msg = MIMEMultipart()

    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    mailServer = smtplib.SMTP(smtp_server, smtp_port)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(account_address, account_password)
    mailServer.sendmail(account_address, to, msg.as_string())
    mailServer.close()

def get_lock(process_name):
    """Function that creates a thread process lock for the OS

    Doing this avoids that out processes get garbage-collected for long executions.

    Arguments:
        process_name {str} -- name for the locked process

    Returns:
        bool -- Returns True if the lock was acquired, False otherwise.
    """
    global lock_socket   # Without this our lock gets garbage collected
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + process_name)
    except socket.error:
        return False
    return True

def run_EF5(ef5Path, hot_folder_path, control_file, log_file):
    """Run EF5 as a subprocess call

    Based on the command:

        subprocess.call(ef5Path + " " + tmpOutput + "flash"+config_file.abbreviation+"_" + systemModel + ".txt >" + tmpOutput + "ef5.log", shell=True)

    Arguments:
        ef5Path {str} -- Path to EF5 binary
        hot_folder_path {str} -- Path to the current run's "hot" foler
        control_file {str} -- path to the control file fir the simulation
        log_file {str} -- path to the log file for this run
    """
    subprocess.call(ef5Path + " " + control_file + " > " + hot_folder_path + log_file, shell=True)


def merge_EF5(folder_path, subdomain_folders, file_name):
    """
    This function merges outputs from multiple EF5 sub-domains in cases where a large domainis divided for computational performance. All sub-domains must have the same geo-spatial attributes (extent, pixel size)
    """

    gdal_cmd_prefix = "/home/ec2-user/anaconda3/bin/gdal_merge.py -a_nodata -9999 -co COMPRESS=Deflate -o "

    #Build sub-domain folder - filename pairs
    subdom_file_pairs = []
    for subdomain in subdomain_folders:
        subdom_file_pairs.append(subdomain + file_name)

    #Join all sub-domain folder - filename pairs
    subdom_argument = " ".join(subdom_file_pairs)

    #Run GDAL merge command
    print(gdal_cmd_prefix + folder_path + file_name + " " + subdom_argument)
    subprocess.call(gdal_cmd_prefix + folder_path + file_name + " " + subdom_argument, shell=True)

def postprocess_EF5(current_q_file, folder_path, output_ti_filename, unitq_file_name):
    """
    This function makes a system call to "simple_compute_track_impact_probability.py" to computed probability of track impact based on Q grids from EF5. Resulting files are then processed (compressing and "stamping" following a pre-specified naming convention) for permanent storage

     Arguments:
         current_q_file {str} -- Path to EF5 binary
         folder_path {str} -- Path to EF5 outputs (merged)
         output_ti_filename {str} -- file name of probability CSV file
         unitq_file_name {str} -- file name of Unit Q CSV file
    """

    #Get filename only (no full path)
    fname_only = os.path.basename(current_q_file)

    #System call of script that computes the probability of Track Impact
    print("python simple_compute_track_impact_probability.py " + current_q_file + " " + folder_path)
    subprocess.call("/home/ec2-user/anaconda3/bin/python /home/ec2-user/Scripts/post_processing/simple_compute_track_impact_probability.py " + current_q_file + " " + folder_path, shell=True)

    #System calls to gzip CSV file and change name
    subprocess.call("/usr/bin/gzip " + folder_path + "ti_prob." + fname_only[:-4] + ".csv", shell=True)
    subprocess.call("/usr/bin/mv " + folder_path + "ti_prob." + fname_only[:-4] + ".csv.gz " + output_ti_filename, shell=True)

    subprocess.call("/usr/bin/gzip " + folder_path + "unitq." + fname_only[:-4] + ".csv", shell=True)
    subprocess.call("/usr/bin/mv " + folder_path + "unitq." + fname_only[:-4] + ".csv.gz " + unitq_file_name, shell=True)

def get_geotiff_datetime(geotiff_path):
    """Funtion that extracts a datetime object corresponding to a Geotiff's timestamp

    Arguments:
        geotiff_path {str} -- path to the geotiff to extract a datetime from

    Returns:
        datetime -- datetime object based on geotiff timestamp
    """
    geotiff_file = geotiff_path.split('/')[-1]
    geotiff_timestamp = geotiff_file.split('.')[3]
    geotiff_datetime = dt.strptime(geotiff_timestamp, "%Y%m%d_%H%M00")
    return geotiff_datetime

def cleanup_precip(current_datetime, max_datetime, geotiff_precip_path):
    """Function that cleans up the precip folder for the current EF5 run

    Arguments:
        current_datetime {datetime} -- datetime object for the current time step
        max_datetime {datetime} -- datetime object representing the maximum datetime in the past
        geotiff_precip_path {str} -- path to the geotiff precipitation folder
    """
    qpes = []
    qpfs = []

    # List all precip files
    precip_files = os.listdir(geotiff_precip_path)

    # Segregate between QPEs and QPFs
    for file in precip_files:
        if "qpe" in file:
            qpes.append(file)
        elif "qpf" in file:
            qpfs.append(file)

    # Delete all QPE files older than max_timestamp
    for qpe in qpes:
        geotiff_datetime = get_geotiff_datetime(geotiff_precip_path + qpe)
        if(geotiff_datetime > max_datetime):
            os.remove(geotiff_precip_path + qpe)

    # Delete all QPF files older that current_datetime
    # QPFs newer than current_datetime will be overwritten when placed in the precip folder.
    for qpf in qpfs:
        geotiff_datetime = get_geotiff_datetime(geotiff_precip_path + qpf)
        if(geotiff_datetime > current_datetime):
            os.remove(geotiff_precip_path + qpf)


def get_new_precip(current_timestamp, netcdf_feed_path, geotiff_precip_path):
    """Function that brings new real-time precipitation into the GeoTIFF precip folder

    Based on Jeremy Stemo's API:
        from swissmeteo import Swissmeteo
        sm = SwissMeteo(“/directory/of/archive”)
        sm.latest_netcdf_timestep()
        sm.is_netcdf_available(timestep)
        sm.write_geotiffs(end_timestep, dest_dir_path, prev_qpe_count=3)

    Arguments:
        current_timestamp {datetime} -- current time step's timestamp
        netcdf_feed_path {str} -- path to the NetCDF precip data feed
        geotiff_precip_path {str} -- path to the GeoTIFF precip archive

    Returns:
        ahead {bool} -- Returns True if the latest NetCDF timestamp is agead of the current time step
        gap {bool} -- Returns True if there is a gap larger than 10min between the latest NetCDF timestamp and the current time step
        exists {bool} -- Returns True there is a NetCDF file in the archive for the current time step
    """
    netcdf_archive = Swissmeteo(netcdf_feed_path)
    latest_netcdf = netcdf_archive.latest_netcdf_timestep()
    ahead = None
    gap = None
    exists = None

    # If the latest rainfall NetCDF corresponds to the current time step
    if latest_netcdf <= current_timestamp:
        # and if the time difference betwen the current timestep and the latest NetCDF is less than 10min
        if current_timestamp - latest_netcdf <= timedelta(minutes=10):
        # get the last hour of QPE data and the latest QPFs into the precip folder
            netcdf_archive.write_geotiffs(current_timestamp, geotiff_precip_path, prev_qpe_count=6)
            ahead = False
            gap = False
            exists = True
        else:
            print("There's more than a 10min gap between now and the latest NetCDF!!!")
            print("Current:", current_timestamp)
            print("Latest:", latest_netcdf)
            found = False
            attempts = 1
            while not found:
                previous_timestamp = current_timestamp - timedelta(minutes= attempts * 10)
                print("Attempt:", attempts, " Previous:", previous_timestamp)
                try:
                    netcdf_archive.write_geotiffs(previous_timestamp, geotiff_precip_path, prev_qpe_count=6)
                    found = True
                    ahead = False
                    gap = True
                    exists = True
                except:
                    attempts += 1
                    if attempts == 3:
                        ahead = False
                        gap = True
                        exists = False
                        break
    # If the latest rainfall NetCDF is ahead of the current time step
    else:
        # look for the current time step in the archive
        current_netcdf = netcdf_archive.is_netcdf_available(current_timestamp)
        # if it exists
        if(current_netcdf is not None):
             # get the previpus hour of QPE data and the latest QPFs into the precip folder
            netcdf_archive.write_geotiffs(current_timestamp, geotiff_precip_path, prev_qpe_count=6)
            ahead = True
            gap = False
            exists = True
        else:
            print("No NetCDF file exists for the current timestep!!!")
            ahead = True
            gap = False
            exists = False

    return ahead, gap, exists


#TODO: Write this function!!!
def fill_gap(current_timestamp, geotiff_precip_path):
    pass


"""
Run the main() function when invoked as a script
"""
if __name__ == "__main__":
    main(sys.argv)
