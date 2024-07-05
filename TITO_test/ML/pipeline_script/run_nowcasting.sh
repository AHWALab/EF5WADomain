#!/bin/bash

## Run the nowcasting pipeline

#SBATCH --job-name=IMERGnowcast
#SBATCH --output=nowcast.out
#SBATCH --error=nowcast.err
#SBATCH --partition=SOE_efthymios
#SBATCH --account=efthymios
#SBATCH --ntasks-per-node=1 # request X CPU cores for the run
##SBATCH -t 14-0:00
#SBATCH --mem=16000   # requested X GB of RAM on a node


# 1. Prepare the Environment for the run
#source /vol_efthymios/NFS07/Data/miniconda3/profile.d/conda.sh
#conda activate


# 2. Run nowcasting codes

python m_tif2h5py.py \
'/vol_efthymios/NFS07/en279/SERVIR/temp/' \
'/vol_efthymios/NFS07/en279/SERVIR/temp/input_imerg.h5'

python m_nowcasting.py \
'/vol_efthymios/NFS07/en279/SERVIR/nowcasting' \
'/vol_efthymios/NFS07/en279/SERVIR/temp/ConvLSTM_Config.py' \
'/vol_efthymios/NFS07/en279/SERVIR/temp/imerg_only_mse_params.pth' \
False \
'/vol_efthymios/NFS07/en279/SERVIR/temp/input_imerg.h5' \
'/vol_efthymios/NFS07/en279/SERVIR/temp/output_imerg.h5'
#export HDF5_USE_FILE_LOCKING=FALSE

python m_h5py2tif.py \
'/vol_efthymios/NFS07/en279/SERVIR/temp/output_imerg.h5' \
'/vol_efthymios/NFS07/en279/SERVIR/temp/imerg_giotiff_meta.json' \
'/vol_efthymios/NFS07/en279/SERVIR/temp/'


# 3. Run EF5
/vol_efthymios/NFS07/en279/SERVIR/EF5_WA/ef5 /vol_efthymios/NFS07/en279/SERVIR/EF5_WA/EF5WADomain/ef5_westafrica_control.txt




#conda deactivate
