#!/bin/csh

set outFolder=/Users/hvergaraarrieta/Documents/GitHub/FFWestAfrica/data/WEST_AFRICA/consolidated/

foreach file (*_Q_Day.csv)
	set station=`echo "$file" | cut -d "_" -f1`
	tr "[;]" "[,]" < "$file" | sed -e s/"-999.000"/"-9999"/g | awk -F, 'BEGIN { OFS = FS } { if ($2 == "") $2 = "-9999"; print }' > ${outFolder}"$station"_daily_Q.csv
end

