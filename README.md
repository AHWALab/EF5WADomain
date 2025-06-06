# Flash Flood Forecasting System for West Africa and Ghana

This repository contains EF5 computational domain for West Africa and Ghana, documentation, data, and results from the research work done for NASA's SERVIR-West Africa project on developing a flash flood forecasting system in the West Africa domain (WA) (1km resolution) and Ghana domain (GH) (1km and 90m resolution).


## Contents

**1) GHANA_domain:**
- **GIS**: GIS files used to configure the study region, also flash flood event locations.
- **DATA_obs**: Observational streamflow data from different entities.
- **Model_config**: Datasets needed to run Ghana high resolution model (90m), such as basic grid files, parameters, and forcings. This folder also contains instructions and inputs to calculate CREST and KW parameters.
- **Results:**: Calibration baseline and Seasonal Calibration for Ghana model at 90m and 1km.

**2) WEST_AFRICA_domain:**
- **Data_obs:** Observational streamflow data from different entities.
- **GIS:** GIS files used to configure the study region such as shapefile of countries included in the EF5 domain and raster with a mask of major basins.
- **Model_config:** All basic files (DEM and its derivatives), parameters for CREST and Kinematic Wave models, and control file to run simulations over selected basins in West Africa.
- **Results:** Baseline simulations perfomed over the entire domain. Pre-computed outputs from a simulation based on this set-up are included.


## References

Vergara, H., Kirstetter, P.E., Gourley, J.J., Flamig, Z.L., Hong, Y., Arthur, A. and Kolar, R., 2016. Estimating a-priori kinematic wave model parameters based on regionalization for flash flood forecasting in the Conterminous United States. Journal of Hydrology, 541, pp.421-433.

Clark, R.A., Flamig, Z.L., Vergara, H., Hong, Y., Gourley, J.J., Mandl, D.J., Frye, S., Handy, M. and Patterson, M., 2017. Hydrological modeling and capacity building in the Republic of Namibia. Bulletin of the American Meteorological Society, 98(8), pp.1697-1715.
