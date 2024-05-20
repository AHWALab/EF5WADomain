#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 22:35:03 2018

@author: researchvisitor
"""

#from sys import argv
import queue as qu
from threading import Thread
import os
import subprocess as sp
import datetime as dt
import glob
import numpy as np
import pandas as pd

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

def worker():
    while True:
        #Obtain string array of filenames and folders 
        args = qu.get()

        # Forecast date
        w_directory = args[0]
        c_forecast = args[1]
        forecast_hour = args[2]
		
	# General variables -----------------------
        webURL = 'https://data.rda.ucar.edu/ds084.1/' + c_forecast.strftime('%Y') + '/' + c_forecast.strftime('%Y%m%d') + '/' 
        # Valid forecast date
        FullDate = c_forecast.strftime('%Y%m%d%H')
        Year = c_forecast.strftime('%Y')
        YMD = c_forecast.strftime('%Y%m%d')
        TrueDate = c_forecast + dt.timedelta(hours=forecast_hour)
        DateStamp = TrueDate.strftime('%Y%m%d%H')
        # Forecast hour as string
        fcst_hour = '{0:03d}'.format(int(forecast_hour))
        raw_grib_file = 'gfs.0p25.' + FullDate + '.f' + fcst_hour + '.grib2'
        local_raw_grib_file = w_directory + '/gfs.0p25.' + FullDate + '.f' + fcst_hour + '.grib2'
        # Template and post-processed VRT
        vrt_template = w_directory + '/' + raw_grib_file + '.pre_vrt' #gfsworld.template.vrt'
        vrt_file = w_directory + '/' + FullDate + '/gfsworld.' + FullDate + '.f' + fcst_hour + '.vrt'
        # Final TIF product
        tif_product = w_directory + '/' + FullDate + '/gfs.' + DateStamp + '.tif'


	# package = [working_directory, current_forecast, hours2target, gfs_variables.Band[0], true_datestamp.strftime('%Y%m%d%H') + '.tif', gfs_variables]
	# Download file
        #print('wget -P ' + working_directory + ' "' + webURL + raw_grib_file + '"')        
        sp.call('wget -P ' + working_directory + ' "' + webURL + raw_grib_file + '"', shell=True)
 
        # IN THE FUTURE, ADD A FOR LOOP FOR MULTIPLE BANDS
        sp.call('./getGRIB2_Band.csh ' + raw_grib_file, shell=True)
        var_file = 'gfs_variables_' + raw_grib_file + '.csv'
        # Read this GRIB's band files
        gfs_variables = pd.read_csv(var_file) 
        tg_band = gfs_variables.Band[0]

        # Extract a band from GRIB2 file
        tif_file_pre = w_directory + '/' + FullDate + '/gfsworld.' + FullDate + '.f' + fcst_hour + '.tif'

        #print('gdal_translate -co COMPRESS=Deflate -b ' + str(tg_band) + ' ' + local_raw_grib_file + ' ' + tif_file_pre)
        sp.call('gdal_translate -co COMPRESS=Deflate -b ' + str(tg_band) + ' ' + local_raw_grib_file + ' ' + tif_file_pre, shell=True) 

        # Substitute new GTIFF in VRT template file
        #print('sed -e s:"{GTIFF}":"' + tif_file_pre + '":g < ' + vrt_template + ' > ' + vrt_file)
        sp.call('sed -e s:"{GTIFF}":"' + tif_file_pre + '":g < ' + vrt_template + ' > ' + vrt_file, shell=True)

        # Subset to region of interest
        gdal_prefix = 'gdalwarp -dstnodata -9999 -co COMPRESS=Deflate -ot Float32 -te -21.4 -2.9 30.4 33.1 -tr 0.25 -0.25 '
        #print(gdal_prefix + vrt_file + ' ' + tif_product)
        sp.call(gdal_prefix + vrt_file + ' ' + tif_product, shell=True) 

        # Clean folder
        #print('rm ' + local_raw_grib_file)
        sp.call('rm ' + local_raw_grib_file + ' ' + tif_file_pre + ' ' + vrt_file + ' ' + var_file + ' ' + vrt_template, shell=True)

        #Complete worker's task
        qu.task_done()

#Initiate Queue and Workers
qu = qu.Queue()
numworkers = 15 #This is the number of simultaneous runs. Be mindful of number of CPUs and memory 
for i in range(numworkers):
        t = Thread(target=worker)
        t.daemon = True
        t.start()

# Main directory
working_directory = '/hydros/humberva/EF5/Global/Africa_NASASERVIR/west_africa/regional_scale/GFS'

# The process will only download data for a target date
target_start_date = dt.datetime(2018,6,19,12,0,0)
# but, it will consider mutliple dates to cover an event
sliding_date = target_start_date
target_end_date = dt.datetime(2018,6,20,12,0,0)
# Max/Min forecast horizons in hours
max_fcst_horizon = 5*24 # 5 days
min_fcst_horizon = 24
# Forecast update frequency in hours
new_fcst_freq = 6
# Forecast time step
fcst_time_step = 3

while sliding_date <= target_end_date:
    print('Working on target date: ' + sliding_date.strftime('%Y%m%d%H'))
    # Target forecast date for which GFS estimates will be downloaded
    this_target_date = sliding_date

    # Earliest forecast for the target date
    this_start_forecast = this_target_date - dt.timedelta(hours=max_fcst_horizon)

    current_forecast = this_start_forecast
    while current_forecast < this_target_date:
        # Make directory to store forecast rainfall file. Ignore errors as necessary
        outputpath = working_directory + '/' + current_forecast.strftime('%Y%m%d%H')
        sp.call('mkdir ' + outputpath, shell=True)

        # Establish how far back you need to go
        total_hours2target = (this_target_date - current_forecast).total_seconds()/3600.0
        
        for hours2target in np.arange(fcst_time_step,total_hours2target+fcst_time_step,fcst_time_step):
            c_file = current_forecast.strftime('%Y') + '/' + current_forecast.strftime('%Y%m%d') + '/gfs.0p25.' + current_forecast.strftime('%Y%m%d%H') + '.f' + '{0:03d}'.format(int(hours2target)) + '.grib2'
            print('Processing forecast ' + '{0:03d}'.format(int(hours2target)) + ' launched on ' + current_forecast.strftime('%Y%m%d%H'))
            print('Downloading ' + c_file)

            # Check if the data already exists. If so, skip downloading and process
            true_datestamp = current_forecast + dt.timedelta(hours=hours2target)
            FileExist = glob.glob(outputpath + '/gfs.' + true_datestamp.strftime('%Y%m%d%H') + '.tif')

            if (len(FileExist) == 0):
                # In sequence
                #downloadNprocess(c_file,current_forecast,hours2target,outputpath)
                #In parallel
                #tp.apply_async(downloadNprocess, [c_file,current_forecast,hours2target,outputpath])
		# Build package with arguments
                package = [working_directory, current_forecast, hours2target]

		#Pass string array of arguments
                qu.put(package) 	 
            else:
                print(c_file + ' has already been processed.')

        # Advance valid forecast start
        current_forecast = current_forecast + dt.timedelta(hours=new_fcst_freq)

    # Advance target date 
    sliding_date = sliding_date + dt.timedelta(hours=fcst_time_step)

#block until all tasks are done
qu.join()
