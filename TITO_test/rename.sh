#!/bin/bash

# Directorio con los archivos a renombrar
DIRECTORIO="/Users/vrobledodelgado/Documents/GitHub/EF5WADomain/TITO_test/qpf_store"

# Iterar sobre cada archivo en el directorio
for ARCHIVO in "$DIRECTORIO"/*.tif; do
  # Obtener el nombre del archivo sin el directorio
  NOMBRE_ARCHIVO=$(basename "$ARCHIVO")
  
  # Quitar la extensión .tif del nombre del archivo
  BASE_NOMBRE="${NOMBRE_ARCHIVO%.tif}"
  
  # Crear el nuevo nombre del archivo
  NUEVO_NOMBRE="imerg.qpf.$BASE_NOMBRE.30minAccum.tif"
  
  # Renombrar el archivo
  mv "$ARCHIVO" "$DIRECTORIO/$NUEVO_NOMBRE"
done
