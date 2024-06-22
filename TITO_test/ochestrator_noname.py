"""
West Africa real-time model/subdomain execution script
Contributors:
Vanessa Robledo - vrobledodelgado@uiowa.edu
Humberto Vergara - humberto-vergaraarrieta@uiowa.edu
V.1.0 - February 01, 2024

This script consolidates execution routines in a single script, while
ingesting a "configuration file" from where a given model can be specified for a
given domain. Please use this script and a configuration file as follows:

    $> python final_name.py <configuration_file.py>

Said configuration file should contain the each of its variables populated, as can be
seen in the following example configuration file contents:

SURGE: System for Urban and Regional Geospatial Environmental flood forecasting
TORRENT: Total Operational Response for Rapid and Enhanced Notification of Torrential floods
SWIFT: System for West Africa Immediate Flood Tracking
SPATE: System for Predictive Analysis and Tracking of flash Events
HARMONY: Hydrological and Regional Machine Learning Operational Network for Yield
RAFT: Real-time Analysis and Flooding Tool
HARBOR: Hydrological Analysis and Real-time Broadcast for Operational Response
SHIELD: System for Hydrological and Inundation Early-warning and Detection

"""
#%%
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
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from multiprocessing.pool import ThreadPool
import requests
from bs4 import BeautifulSoup
import datetime as DT
import osgeo.gdal as gdal
from osgeo.gdal import gdalconst
from osgeo.gdalconst import GA_ReadOnly
import time
"""
Setup Environment Variables for Linux Shared Libraries and OpenMP Threads
"""
os.environ['LD_LIBRARY_PATH'] = '/usr/local/lib'
os.environ['OMP_NUM_THREADS'] = '1'

#domain = "WestAfrica"
#subdomain = "Regional"
#model_resolution = "1km"
#systemModel = "crest"
#systemName = systemModel.upper() + " " + domain.upper() + " " + subdomain.upper()
#ef5Path = "/vol_efthymios/NFS07/en279/SERVIR/EF5_WA/ef5"
#statesPath = "states/"
precipFolder = "precip/"
#modelStates = ["crest_SM", "kwr_IR", "kwr_pCQ", "kwr_pOQ"]
#templatePath = "templates/"
#templates = "ef5_control_template.txt"
#DATA_ASSIMILATION = False
#assimilationPath = ""
#assimilationLogs = []
dataPath = "outputs/"
qpf_store_path = 'qpf_store/'
#tmpOutput = dataPath + "tmp_output_" + systemModel + "/"
#SEND_ALERTS = False
#smtp_server = "smtp.gmail.com"
#smtp_port = 587
#account_address = "model_alerts@gmail.com"
#account_password = "supersecurepassword9000"
#alert_sender = "Real Time Model Alert" # can also be the same as account_address
#alert_recipients = ["fixer1@company.com", "fixer2@company.com", "panic@company.com",...]
#copyToWeb = False
HindCastMode = True
HindCastDate = "2020-10-10 09:00" #"%Y-%m-%d %H:%M"  #Ghana dates is this date in LT, we have to converto to UTC
# Email associated to GPM account
email = 'vrobledodelgado@uiowa.edu'
server = 'https://jsimpsonhttps.pps.eosdis.nasa.gov/imerg/gis/early/'


def main(args):
    """Main function of the script.

    This function reads the real-time configuration script, makes sure the necessary files to run
    FLASH exist and are in the right place, runs the model(s), writes the outputs and states, and
    reports vie email if an error occurs during execution.

    Arguments:
        args {list} -- the first argument ([1]) corresponds to a real-time configuration file.
    """

    # # Read the configuration file
    # #config_file = __import__(args[1].replace('.py', ''))
    # import westafrica1km_config_VR as config_file
    # domain = config_file.domain
    # subdomain = config_file.subdomain
    # systemModel = config_file.systemModel
    # systemName = config_file.systemName
    # ef5Path = config_file.ef5Path
    # precipFolder = config_file.precipFolder
    # statesPath = config_file.statesPath
    # modelStates = config_file.modelStates
    # templatePath = config_file.templatePath
    # template = config_file.templates
    # DATA_ASSIMILATION = config_file.DATA_ASSIMILATION
    # assimilationPath = config_file.assimilationPath
    # assimilationLogs = config_file.assimilationLogs
    # dataPath = config_file.dataPath
    # tmpOutput = config_file.tmpOutput
    # SEND_ALERTS = config_file.SEND_ALERTS
    # smtp_server = config_file.smtp_server
    # smtp_port = config_file.smtp_port
    # account_address = config_file.account_address
    # account_password = config_file.account_password
    # alert_sender = config_file.alert_sender
    # alert_recipients = config_file.alert_recipients
    # MODEL_RES = config_file.model_resolution
    # # SampleTIFF = config_file.sample_geotiff
    # # product_Path = config_file.product_Path
    # geoFile = "/home/ec2-user/Scripts/post_processing/georef_file.txt"
    # # thread_th = config_file.thread_th
    # # distance_th = config_file.distance_th
    # # Npixels_th = config_file.Npixels_th
    # copyToWeb = config_file.copyToWeb
    # HindCastMode = config_file.HindCastMode
    # HindCastDate = config_file.HindCastDate
    # server = config_file.server #'https://arthurhouhttps.pps.eosdis.nasa.gov/gpmdata'
    # subfolder = config_file.subfolder # '/gis/'
    # file_prefix = config_file.file_prefix #'3B-HHR-GIS.MS.MRG.3IMERG.'
    # file_suffix = file_prefix.file_suffix #'.V07A.tif'
    # email = config_file.email
    
    # Real-time mode or Hindcast mode
    # Figure out the timing for running the current timestep
    if HindCastMode == True:
        currentTime = dt.strptime(HindCastDate, "%Y-%m-%d %H:%M")  ##informar al usuario que el timezone es utc
        print("*** Starting hindcast run cycle at " + currentTime.strftime("%Y%m%d_%H%M") + " UTC ***")        
    else:
        currentTime = dt.utcnow()
        print("*** Starting real-time run cycle at " + currentTime.strftime("%Y%m%d_%H%M") + " UTC ***")

    # Round down the current minutess to the nearest 30min increment in the past
    min30 = int(np.floor(currentTime.minute / 30.0) * 30)
    # Use the rounded down minutes as the timestamp for the current time step
    currentTime = currentTime.replace(minute=min30, second=0, microsecond=0)

    # Configure the system to run once every hour
    # Start the simulation using QPEs from 4-6 hours ago
    systemStartTime = currentTime - timedelta(minutes=270) #4h,30 min
    # Save states for the current run with the current time step's timestamp
    systemStateEndTime = currentTime - timedelta(minutes=240) #4h
    # Run warm up using the last hour of data until the current time step
    systemWarmEndTime = currentTime - timedelta(minutes=240)
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
        cleanup_precip(currentTime, failTime, precipFolder,qpf_store_path)
        # Get the necessary QPEs and QPFs for the current time step into the GeoTIFF precip folder
        # store whether there's a QPE gap or the QPEs for the current time step is missing
        get_new_precip(currentTime, server, precipFolder, email)
        #Produce ML qpf from currentTime - 4h till currentime +2h
        run_ml_nowcast(currentTime,precipFolder)
    except:
        print('fallo el nowcast')
        
def get_geotiff_datetime(geotiff_path):
    """Funtion that extracts a datetime object corresponding to a Geotiff's timestamp

    Arguments:
        geotiff_path {str} -- path to the geotiff to extract a datetime from

    Returns:
        datetime -- datetime object based on geotiff timestamp
    """
    geotiff_file = geotiff_path.split('/')[-1]
    geotiff_timestamp = geotiff_file.split('.')[2]
    geotiff_datetime = dt.strptime(geotiff_timestamp, '%Y%m%d%H%M')
    return geotiff_datetime

def cleanup_precip(current_datetime, failTime, precipFolder, qpf_store_path):
    """Function that cleans up the precip folder for the current EF5 run

    Arguments:
        current_datetime {datetime} -- datetime object for the current time step
        max_datetime {datetime} -- datetime object representing the maximum datetime in the past
        geotiff_precip_path {str} -- path to the geotiff precipitation folder
    """
    qpes = []
    qpfs = []
    
    # List all precip files
    precip_files = os.listdir(precipFolder)

    # Segregate between QPEs and QPFs
    for file in precip_files:
        if "qpe" in file:
            qpes.append(file)
        elif "qpf" in file:
            qpfs.append(file)

    #print(qpes)

    # Delete all QPE files older than max_timestamp (-6h)
    for qpe in qpes:
        geotiff_datetime = get_geotiff_datetime(precipFolder + qpe)
        if(geotiff_datetime < failTime):
            os.remove(precipFolder + qpe)

    # Delete all QPF files older than the current_datetime and copy them in the store path
    # QPFs newer than current_datetime will be overwritten when placed in the precip folder.
    for qpf in qpfs:
        geotiff_datetime = get_geotiff_datetime(precipFolder + qpf)
        if(geotiff_datetime < current_datetime):
            shutil.copy2(precipFolder + qpf, qpf_store_path)
            os.remove(precipFolder + qpf)
            
    # Delete all QPF in store folder older than current time - 4h
    qpf_stored_files = os.listdir(qpf_store_path)
    qpf_stored_files = [f for f in qpf_stored_files if f.endswith('.tif')]
    max_qpf = current_datetime - timedelta(hours=4)
    for qpf_stored in qpf_stored_files:
        qpf_datetime = get_geotiff_datetime(qpf_store_path + qpf_stored)
        if(qpf_datetime < max_qpf):
            os.remove(qpf_store_path + qpf_stored)
    
    print('*** Precip folder cleaning completed ***')
    
def extract_timestamp(filename):
    date_str = filename.split('.')[4][:8]  # '20201001'
    time_str = filename.split('-')[3][1:]  # 'S000000' -> '000000'
    date_time_str = date_str + time_str  # '20201001000000'
    final_datetime = datetime.datetime.strptime(date_time_str, '%Y%m%d%H%M%S')+timedelta(minutes=30)
    return final_datetime
            
def retrieve_imerg_files(url, email, HindCastMode, date):
    if HindCastMode:
        folder = date.strftime('%Y/%m/')
        url_server = url + '/' + folder
    else: 
        url_server = url
    # Send a GET request to the URL
    response = requests.get(url_server, auth=(email, email))

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the content of the response with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links on the page
        links = soup.find_all('a')

        # Extract file names from the links
        files = [link.get('href') for link in links if link.get('href').endswith('30min.tif')]
    else:
        print(f"Failed to retrieve the directory listing. Status code: {response.status_code}")
        
    return files 

def get_gpm_files(initial_timestamp, final_timestamp, ppt_server_path ,email):
    #path server
    server = ppt_server_path
    file_prefix = '3B-HHR-E.MS.MRG.3IMERG.'
    file_suffix = '.V07B.30min.tif'
    
    # Domain coordinates (This part must be changed)
    xmin = -180
    xmax = 180
    ymin = -90
    ymax = 90
    
    final_date = final_timestamp + timedelta(minutes=30)
    delta_time = datetime.timedelta(minutes=30)
    
    # Loop through dates
    current_date = initial_timestamp
    #acumulador_30M = 0
    
    while (current_date < final_date):
        initial_time_stmp = current_date.strftime('%Y%m%d-S%H%M%S')
        final_time = current_date + DT.timedelta(minutes=29)
        final_time_stmp = final_time.strftime('E%H%M59')
        final_time_gridout = current_date + DT.timedelta(minutes=30)
        folder = current_date.strftime('%Y/%m/')
        
        # #finding accum
        hours = (current_date.hour)
        minutes = (current_date.minute)
    
        # # Calculate the number of minutes since the beginning of the day.
        total_minutes = hours * 60 + minutes
    
        date_stamp = initial_time_stmp + '-' + final_time_stmp + '.' + f"{total_minutes:04}"

        filename = folder + file_prefix + date_stamp + file_suffix

        print('    Downloading ' + server + '/' + filename)
        try:
            # Download from NASA server
            get_file(filename)
            # Process file for domain and to fit EF5
            # Filename has final datestamp as it represents the accumulation upto that point in time
            gridOutName = precipFolder+'imerg.qpe.' + final_time_gridout.strftime('%Y%m%d%H%M') + '.30minAccum.tif'
            local_filename = file_prefix + date_stamp + file_suffix
            NewGrid, nx, ny, gt, proj = processIMERG(local_filename,xmin,ymin,xmax,ymax)
            filerm = file_prefix + date_stamp + file_suffix
            # Write out processed filename
            WriteGrid(gridOutName, NewGrid, nx, ny, gt, proj)
            os.remove(filerm)
        except Exception as e:
            print(e)
            print(filename)
            pass

        # Advance in time
        current_date = current_date + delta_time
          
def get_file(filename):
   ''' Get the given file from jsimpsonhttps using curl. '''
   url = server + '/' + filename
   cmd = 'curl -sO -u ' + email + ':' + email + ' ' + url
   args = cmd.split()
   process = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   process.wait() # wait so this program doesn't end before getting all files#
   
def ReadandWarp(gridFile,xmin,ymin,xmax,ymax):
    #Read grid and warp to domain grid
    #Assumes no reprojection is necessary, and EPSG:4326
    rawGridIn = gdal.Open(gridFile, GA_ReadOnly)

    # Adjust grid
    pre_ds = gdal.Translate('OutTemp.tif', rawGridIn, options="-co COMPRESS=Deflate -a_nodata 29999 -a_ullr -180.0 90.0 180.0 -90.0")

    gt = pre_ds.GetGeoTransform()
    proj = pre_ds.GetProjection()
    nx = pre_ds.GetRasterBand(1).XSize
    ny = pre_ds.GetRasterBand(1).YSize
    NoData = 29999
    pixel_size = gt[1]

    #Warp to model resolution and domain extents
    ds = gdal.Warp('', pre_ds, srcNodata=NoData, srcSRS='EPSG:4326', dstSRS='EPSG:4326', dstNodata='-9999', format='VRT', xRes=pixel_size, yRes=-pixel_size, outputBounds=(xmin,ymin,xmax,ymax))

    WarpedGrid = ds.ReadAsArray()
    new_gt = ds.GetGeoTransform()
    new_proj = ds.GetProjection()
    new_nx = ds.GetRasterBand(1).XSize
    new_ny = ds.GetRasterBand(1).YSize

    return WarpedGrid, new_nx, new_ny, new_gt, new_proj

def WriteGrid(gridOutName, dataOut, nx, ny, gt, proj):
    #Writes out a GeoTIFF based on georeference information in RefInfo
    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(gridOutName, nx, ny, 1, gdal.GDT_Float32, ['COMPRESS=DEFLATE'])
    dst_ds.SetGeoTransform(gt)
    dst_ds.SetProjection(proj)
    dataOut.shape = (-1, nx)
    dst_ds.GetRasterBand(1).WriteArray(dataOut, 0, 0)
    dst_ds.GetRasterBand(1).SetNoDataValue(-9999.0)
    dst_ds = None

def processIMERG(local_filename,llx,lly,urx,ury):
    # Process grid
    # Read and subset grid
    NewGrid, nx, ny, gt, proj = ReadandWarp(local_filename,llx,lly,urx,ury)
    # Scale value
    NewGrid = NewGrid*0.1
    return NewGrid, nx, ny, gt, proj
                             
def get_new_precip(current_timestamp, ppt_server_path, precipFolder, email):
    """Function that brings latest IMERG precipitation file into the GeoTIFF precip folder

    Arguments:
        current_timestamp {datetime} -- current time step's timestamp
        netcdf_feed_path {str} -- path to the geoTIFF precip data feed --- el httml
        geotiff_precip_path {str} -- path to the GeoTIFF precip archive -- el folder precip 

    Returns:
        ahead {bool} -- Returns True if the latest GeoTIFF timestamp is agead of the current time step
        gap {bool} -- Returns True if there is a gap larger than 30min between the latest GeoTIFF timestamp and the current time step
        exists {bool} -- Returns True there is a GeoTIFF file in the archive for the current time step
    """
    #Obtainign the lates time step in the imerg server 
    # server_files = retrieve_imerg_files(ppt_server_path, email, HindCastMode, )
    # most_recent_IMERG = max(server_files, key=lambda x: datetime.datetime.strptime(x[23:39], '%Y%m%d-S%H%M%S'))
    # formatted_latest_imerg = datetime.datetime.strptime(most_recent_IMERG[23:39], '%Y%m%d-S%H%M%S')  #last imerg on server available
    
    #Look for the most recent file in precip folder
    #Obtainign the latest time step in the folder
    files_folder = os.listdir(precipFolder)
    tif_files = [f for f in files_folder if "qpe" in f]
    
    #the first hour of nowcast files will be current time - 3h
    nowcast_older = current_timestamp - timedelta(hours = 3)
    print('*** Retrieven IMERG files ***')
    if tif_files:
        print("There are IMERG files in the precip folder")
        # Extract the most recent date from files
        latest_date = max(tif_files, key=lambda x: datetime.datetime.strptime(x[10:22], '%Y%m%d%H%M'))
        formatted_latest_pptfile = datetime.datetime.strptime(latest_date[10:22], '%Y%m%d%H%M') #last file on precip
        #if the latest imerg file in folder corresponds to the older nowcast file (current time - 3h)
        if formatted_latest_pptfile <= nowcast_older: ###Cuando podria pasar lo contrario HUMBERTO!!!
            # and if the time difference betwen the current timestep and the latest imerg in folder is less than 30 min.
            if nowcast_older - formatted_latest_pptfile <= timedelta(minutes=60):
                print('    There are less than 30 min')
                #List the missing dates between lastes ppt file and current timestep
                missing_dates = []
                # Iterar desde la fecha del archivo más reciente hasta el timestamp actual en intervalos de 30 minutos
                next_timestamp = formatted_latest_pptfile + timedelta(minutes=30)
                while next_timestamp < nowcast_older:
                    missing_dates.append(next_timestamp)
                    next_timestamp += timedelta(minutes=30)
                for date in missing_dates:
                    server_files = retrieve_imerg_files(ppt_server_path, email, HindCastMode, date)
                    # Verificar si el timestamp está en la lista de archivos
                    timestamps = [extract_timestamp(file) for file in server_files]
                    if date in timestamps:
                        print("    Downloading the last file of precip data")
                        #downloading the file 
                        date_server = date - timedelta(minutes=30)
                        nowcast_older_server = nowcast_older - timedelta(minutes=60) #this is because get imerg files sums up 30 min
                        get_gpm_files(date_server, nowcast_older_server, ppt_server_path, email)
                    else:
                        print("    The file requeried is not available on the IMERG server.")
                        print("    Copying the corresponding file from nowcast store folder")
                        formatted_date = date.strftime('%Y%m%d%H%M')
                        # Buscar el archivo que contenga el string 'formatted_timestamp'
                        file_found = False
                        for filename in os.listdir(qpf_store_path):
                            if formatted_date in filename:
                                # Ruta completa del archivo fuente y destino
                                source_file = os.path.join(qpf_store_path, filename)
                                destination_file = os.path.join(precipFolder, filename)
                                # Copiar el archivo al directorio de destino
                                shutil.copy2(source_file, destination_file)
                                print(f"    File '{filename}' was copied in '{precipFolder}'")
                                file_found = True
                                break
                        if not file_found:
                            print(f"    No se encontró ningún archivo que contenga el string '{formatted_date}'") ###REVISAR HUMBERTO            
            else: 
                print("    There's more than a 30min gap between now and the latest geoTIFF file!!!")
                print("    Last IMERG file:", nowcast_older)
                print("    Latest Geotiff file available in folder:", formatted_latest_pptfile)
                #Downloading imerg files between dates
                nowcast_older_server = nowcast_older - timedelta(minutes=60)
                get_gpm_files(formatted_latest_pptfile, nowcast_older_server, ppt_server_path, email)
                #List the missing dates between lastes ppt file and current timestep
                missing_dates = []
                next_timestamp = formatted_latest_pptfile + timedelta(minutes=30)
                while next_timestamp < nowcast_older:
                    missing_dates.append(next_timestamp)
                    next_timestamp += timedelta(minutes=30)
                for date in missing_dates: #esta seccion hay que mejorarla, para hacer el retrieve 1 solaa vez
                    #aca debe buscar las missing dates en el folder local antes de buscar en el server!!!!!!!!!!!!!!!!
                    server_files = retrieve_imerg_files(ppt_server_path, email, HindCastMode, date)    
                    timestamps = [extract_timestamp(file) for file in server_files]
                    #Looking for timestaps missing in imerg
                    if date not in timestamps:
                        print(f"    File {date} is missing")
                        print("    Copying the corresponding file from nowcast store folder")
                        formatted_date = date.strftime('%Y%m%d%H%M')
                        # Buscar el archivo que contenga el string 'formatted_timestamp'
                        file_found = False
                        for filename in os.listdir(qpf_store_path):
                            if formatted_date in filename:
                                # Ruta completa del archivo fuente y destino
                                source_file = os.path.join(qpf_store_path, filename)
                                destination_file = os.path.join(precipFolder, filename)
                                # Copiar el archivo al directorio de destino
                                shutil.copy2(source_file, destination_file)
                                print(f"    File '{filename}' was copied in '{precipFolder}'")
                                file_found = True
                            if not file_found:
                                print(f"    No se encontró ningún archivo que contenga el string '{formatted_date}'") ###REVISAR HUMBERTO
    else:
        print("    No '.tif' files found in the precip folder.") 
        #si no hay archivos coge el archivo final como el current time 
        #y el inicio va a ser el ultimo del imerg - 6 horas 
        latest_date = current_timestamp
        formatted_latest_date = latest_date
        initial_time = latest_date - timedelta(minutes=360) #failtime
        get_gpm_files(initial_time, formatted_latest_date, ppt_server_path, email)
    print("*** QPE's are complete in precip folder ***")
    
def extract_timestamp_2(filename):
    try:
        date_str = filename.split('.')[2]  # '202010100600'
        return datetime.datetime.strptime(date_str, '%Y%m%d%H%M')
    except (IndexError, ValueError):
        return None
    
def run_ml_nowcast(currentTime,precipFolder):
    #Produce ML qpf from currentTime - 4h till currentime +2h
    init = currentTime - timedelta(hours = 3)
    final = currentTime + timedelta(hours = 2)
    path_nowcast = '/Users/vrobledodelgado/Documents/GitHub/EF5WADomain/TITO_test/nowcast/53'
    # Iterar sobre los archivos en el directorio de origen
    for filename in os.listdir(path_nowcast):
        if filename.endswith(".tif"):
            file_timestamp = extract_timestamp_2(filename)
            if file_timestamp and init <= file_timestamp <= final:
                # Ruta completa del archivo fuente y destino
                source_file = os.path.join(path_nowcast, filename)
                destination_file = os.path.join(precipFolder, filename)
                # Copiar el archivo al directorio de destino
                shutil.copy2(source_file, destination_file)
    print(f"*** Nowcast files were copied to '{precipFolder} ***'")
    
    
#%%              
"""
Run the main() function when invoked as a script
"""
if __name__ == "__main__":
    main(sys.argv)

# %%
