#!/bin/csh

# Get file as input argument
set inFile=$1

# Get temporary meta data file
gdalinfo ${inFile} > ${inFile}.GDALINFO

# Get reference line
set RefLin=`grep -n "Precipitation rate" ${inFile}.GDALINFO | cut -d ":" -f1`

# Look 10 lines preceding reference line
set lineAbove=`expr ${RefLin} - 10`
set Band=`sed -n ${lineAbove},${RefLin}p ${inFile}.GDALINFO | grep "Band" | tail -n 1 | cut -d " " -f2`

# Write to file for further processing
sed -e s/"{BAND}"/${Band}/g < gfs_variables_template.csv > gfs_variables_${inFile}.csv

# Extract MetaData
gdal_translate -b ${Band} ${inFile} ${inFile}.VRT

set DESCRIPTION=`grep "Description" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1` 
set GRIB_COMMENT=`grep "GRIB_COMMENT" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_DISCIPLINE=`grep "GRIB_DISCIPLINE" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_ELEMENT=`grep "GRIB_ELEMENT" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_FORECAST_SECONDS=`grep "GRIB_FORECAST_SECONDS" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_IDS=`grep "GRIB_IDS" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_PDS_PDTN=`grep "GRIB_PDS_PDTN" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_PDS_TEMPLATE_ASSEMBLED_VALUES=`grep "GRIB_PDS_TEMPLATE_ASSEMBLED_VALUES" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_PDS_TEMPLATE_NUMBERS=`grep "GRIB_PDS_TEMPLATE_NUMBERS" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_REF_TIME=`grep "GRIB_REF_TIME" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_SHORT_NAME=`grep "GRIB_SHORT_NAME" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_UNIT=`grep "GRIB_UNIT" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`
set GRIB_VALID_TIME=`grep "GRIB_VALID_TIME" ${inFile}.VRT | cut -d ">" -f2 | cut -d "<" -f1`

#sed -e s:"{GRIB_COMMENT}":"${GRIB_COMMENT}":g < gfsworld.template.vrt > ${inFile}.pre_vrt
#sed -e s/"{DESCRIPTION}"/"${DESCRIPTION}"/g -e s:"{GRIB_COMMENT}":"${GRIB_COMMENT}":g -e s/"{GRIB_DISCIPLINE}"/"${GRIB_DISCIPLINE}"/g -e s/"{GRIB_ELEMENT}"/"${GRIB_ELEMENT}"/g -e s/"{GRIB_FORECAST_SECONDS}"/"${GRIB_FORECAST_SECONDS}"/g -e s/"{GRIB_IDS}"/"${GRIB_IDS}"/g -e s/"{GRIB_PDS_PDTN}"/"${GRIB_PDS_PDTN}"/g -e s/"{GRIB_PDS_TEMPLATE_ASSEMBLED_VALUES}"/"${GRIB_PDS_TEMPLATE_ASSEMBLED_VALUES}"/g -e s/"{GRIB_PDS_TEMPLATE_NUMBERS}"/"${GRIB_PDS_TEMPLATE_NUMBERS}"/g -e s/"{GRIB_REF_TIME}"/"${GRIB_REF_TIME}"/g -e s/"{GRIB_SHORT_NAME}"/"${GRIB_SHORT_NAME}"/g -e s/"{GRIB_UNIT}"/"${GRIB_UNIT}"/g -e s/"{GRIB_VALID_TIME}"/"${GRIB_VALID_TIME}"/g < gfsworld.template.vrt > ${inFile}.pre_vrt 

echo ${GRIB_IDS}

sed -e s:"{DESCRIPTION}":"${DESCRIPTION}":g -e s:"{GRIB_COMMENT}":"${GRIB_COMMENT}":g -e s/"{GRIB_DISCIPLINE}"/"${GRIB_DISCIPLINE}"/g -e s:"{GRIB_ELEMENT}":"${GRIB_ELEMENT}":g -e s:"{GRIB_FORECAST_SECONDS}":"${GRIB_FORECAST_SECONDS}":g -e s/"{GRIB_IDS}"/"${GRIB_IDS}"/g -e s:"{GRIB_PDS_PDTN}":"${GRIB_PDS_PDTN}":g -e s:"{GRIB_PDS_TEMPLATE_ASSEMBLED_VALUES}":"${GRIB_PDS_TEMPLATE_ASSEMBLED_VALUES}":g -e s:"{GRIB_PDS_TEMPLATE_NUMBERS}":"${GRIB_PDS_TEMPLATE_NUMBERS}":g -e s:"{GRIB_REF_TIME}":"${GRIB_REF_TIME}":g -e s:"{GRIB_SHORT_NAME}":"${GRIB_SHORT_NAME}":g -e s:"{GRIB_UNIT}":"${GRIB_UNIT}":g -e s:"{GRIB_VALID_TIME}":"${GRIB_VALID_TIME}":g < gfsworld.template.vrt > ${inFile}.pre_vrt

# Clean up temporary file
rm ${inFile}.GDALINFO
rm ${inFile}.VRT
