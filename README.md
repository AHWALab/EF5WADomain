# Flash Flood Forecasting System for West Africa and Ghana

This repository contains EF5 computational domain for West Africa and Ghana, documentation, data, and results from the research work done for NASA's SERVIR-West Africa project on developing a flash flood forecasting system in the West Africa domain (WA) (1km resolution) and Ghana domain (GH) (1km and 90m resolution).


## Contents

**1) GHANA_domain:**
- **GIS**: GIS files used to configure the study region, also flash flood event locations.
- **DATA_obs**: Observational streamflow data from different entities.
- **Model_config**: Datasets needed to run Ghana high resolution model (90m), such as basic grid files, parameters, and forcings. The kinematic wave parameters are not available in this repository because their size exceeds GitHub's upload limit. Please contact vanessa-robledodelgado@uiowa.edu to request them.
- **Results:**: Calibration baseline and Seasonal Calibration for Ghana model at 90m and 1km.

**2) WEST_AFRICA_domain:**
- **Data_obs:** Observational streamflow data from different entities.
- **GIS:** GIS files used to configure the study region such as shapefile of countries included in the EF5 domain and raster with a mask of major basins.
- **Model_config:** All basic files (DEM and its derivatives), parameters for CREST and Kinematic Wave models, and control file to run simulations over selected basins in West Africa.
- **Results:** Baseline simulations perfomed over the entire domain. Pre-computed outputs from a simulation based on this set-up are included.


## References

Vergara, H., Kirstetter, P.E., Gourley, J.J., Flamig, Z.L., Hong, Y., Arthur, A. and Kolar, R., 2016. Estimating a-priori kinematic wave model parameters based on regionalization for flash flood forecasting in the Conterminous United States. Journal of Hydrology, 541, pp.421-433.

Clark, R.A., Flamig, Z.L., Vergara, H., Hong, Y., Gourley, J.J., Mandl, D.J., Frye, S., Handy, M. and Patterson, M., 2017. Hydrological modeling and capacity building in the Republic of Namibia. Bulletin of the American Meteorological Society, 98(8), pp.1697-1715.

## Presentations

-  Vergara, H. J., Robledo, V., Anagnostopoulos, G., Aravamudan, A., Zhang, X., Nikolopoulos, E. I.,... & Forero, G. (2023). Improving Flash Flood Monitoring and Forecasting Capabilities in West
Africa with Satellite Observations and Precipitation Forecasts. In AGU Fall Meeting 2024. (Vol. 2023, pp. H11A-06).
- Lamichhane, D.; Koukoula, M.; Vergara, H. J.; Robledo, V.; Gourley, J. J., … & Anagnostopoulos, G. C. (2024). Flash flood forecasting in West Africa: Evaluating the performance of regional and global numerical weather prediction models. In AGU Fall Meeting 2024. (Vol. 2024, pp. GC54B-04)
- Zhang, X., Aravamudan, A., Nasibi, M., Robledo, V., Maggioni, V., Vergara, H. J., ... & Anagnostopoulos, G. C. (2024). Enhancing Precipitation Nowcasting in West Africa through IR- Integrated Deep Generative Models. In AGU Fall Meeting 2024. AGU24. (Vol 2024, pp. H34H-05)
- Nikolopoulos, E., Ali, A., Amponsah, W., Anagnostopoulos, G., Aravamudan, A., Gourley, J. J., Robledo V., ... & Zhang, X. (2024). Advancing Flash Flood Forecasting Capabilities in West Africa with Machine Learning and Satellite Observations. In 104th AMS Annual Meeting. AMS.

## Contact
For any questions, contact Vanessa Robledo (vanessa-robledodelgado@uiowa.edu) or Humberto Vergara (humberto-vergaraarrieta@uiowa.edu)
