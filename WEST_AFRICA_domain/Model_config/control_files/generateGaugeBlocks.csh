#!/bin/csh

set locations=GIS/Manually_Corrected_Locations/WestAfrica_Locations_Corrected_HV_v04132024.csv

set nFileLines=75

# Start with a clean file
rm gauges_blocks_ctrl.txt

foreach line (`seq 2 1 $nFileLines`)
	# Get variables
	set station=`sed -n ${line}p ${locations} | cut -d "," -f3 | tr -d '["]'`
	set LAT=`sed -n ${line}p ${locations} | cut -d "," -f2`
	set LON=`sed -n ${line}p ${locations} | cut -d "," -f1`	

	# Write to file
	echo "[gauge ${station}] lat=${LAT} lon=${LON}" >> gauges_blocks_ctrl.txt
end

# Now Basin block
echo "[Basin 0]" >> gauges_blocks_trl.txt
foreach line (`seq 2 1 $nFileLines`)
	set station=`sed -n ${line}p ${locations} | cut -d "," -f3 | tr -d '["]'`
        echo "gauge=${station}" >> gauges_blocks_ctrl.txt
end
