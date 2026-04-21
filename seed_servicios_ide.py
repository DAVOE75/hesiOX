"""
Script para crear la tabla servicios_ide y poblarla con el catálogo inicial.
Ejecutar una sola vez:
    python seed_servicios_ide.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from extensions import db
from models import ServicioIDE

CATALOGO_INICIAL = [
    dict(nombre='IGN MTN25 (WMTS)', pais='🇪🇸 España', tipo='WMTS', categoria='Topográfico',
         url='https://www.ign.es/wmts/mapa-raster?request=getTile&layer=MTN25&TileMatrixSet=GoogleMapsCompatible&TileMatrix={z}&TileRow={y}&TileCol={x}&format=image/jpeg',
         attribution='© IGN España'),
    dict(nombre='PNOA Actual (WMTS)', pais='🇪🇸 España', tipo='WMTS', categoria='Ortofoto',
         url='https://www.ign.es/wmts/pnoa-ma?request=getTile&layer=OI.OrthoimageCoverage&TileMatrixSet=GoogleMapsCompatible&TileMatrix={z}&TileRow={y}&TileCol={x}&format=image/jpeg',
         attribution='© PNOA IGN'),
    dict(nombre='IGN Base (WMTS)', pais='🇪🇸 España', tipo='WMTS', categoria='Base',
         url='https://www.ign.es/wmts/ign-base?request=getTile&layer=IGNBaseTodo&TileMatrixSet=GoogleMapsCompatible&TileMatrix={z}&TileRow={y}&TileCol={x}&format=image/png',
         attribution='© IGN España'),
    dict(nombre='MDT LiDAR 5m (WMTS)', pais='🇪🇸 España', tipo='WMTS', categoria='Elevación',
         url='https://wmts-mapa-lidar.idee.es/lidar?request=getTile&layer=EL.GridCoverageDSM&TileMatrixSet=GoogleMapsCompatible&TileMatrix={z}&TileRow={y}&TileCol={x}&format=image/png',
         attribution='© IGN España'),
    dict(nombre='Catastro (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Catastro',
         url='https://www.catastro.meh.es/INSPIRE/buildings/ES.SDGC.BU.wms',
         capas='CP.CadastralParcel', attribution='© Sede Electrónica del Catastro'),
    dict(nombre='Catastro (WMTS)', pais='🇪🇸 España', tipo='WMTS', categoria='Catastro',
         url='https://ovc.catastro.meh.es/cartografia/WMTS/ovccatastro.aspx?Request=getTile&Service=WMTS&Layer=Catastro&TileMatrixSet=GoogleMapsCompatible&TileMatrix={z}&TileRow={y}&TileCol={x}&Format=image/png',
         attribution='© Catastro'),
    dict(nombre='SIGPAC (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Agrario',
         url='https://sigpac.mapama.gob.es/wms/wms.aspx', capas='RECINTO', attribution='© FEGA / MAPA'),
    dict(nombre='SIOSE (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Usos del Suelo',
         url='https://servicios.idee.es/wms-inspire/ocupacion-suelo', capas='LC.LandCoverSurfaces', attribution='© IGN España'),
    dict(nombre='Minutas IGN (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Histórico',
         url='https://www.ign.es/wms/minutas-cartograficas', capas='minutas', attribution='© IGN España'),
    dict(nombre='Vuelo 1945 PNOA (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Histórico',
         url='https://wms.mapama.gob.es/sig/Cartografia/OrtosHist/wms.aspx', capas='Vuelo_Interministerial45-46', attribution='© IGN España'),
    dict(nombre='Vuelo 1956 PNOA (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Histórico',
         url='https://wms.mapama.gob.es/sig/Cartografia/OrtosHist/wms.aspx', capas='Vuelo_Americano56-57_Serie_B', attribution='© IGN España'),
    dict(nombre='Hidrografía IGN (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Hidrografía',
         url='https://servicios.idee.es/wms-inspire/hidrografia', capas='HY.PhysicalWaters.Waterbodies', attribution='© IGN España'),
    dict(nombre='Planimetrías IGN (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Histórico',
         url='https://www.ign.es/wms/planimetrías', capas='planimetrias', attribution='© IGN España'),
    dict(nombre='IECA Andalucía (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Regional',
         url='https://www.ideandalucia.es/wms/mdt_2005', capas='mdt_2005', attribution='© IECA'),
    dict(nombre='ICV Valencia (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Regional',
         url='https://terramapas.icv.gva.es/0002CGPV3', capas='CGPV3_30', attribution='© ICV'),
    dict(nombre='ICGC Catalunya (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Regional',
         url='https://geoserveis.icgc.cat/servei/catalunya/mapa-topografic-5000/wms', capas='mtc5m', attribution='© ICGC'),
    dict(nombre='DGT Ortofoto (WMS)', pais='🇵🇹 Portugal', tipo='WMS', categoria='Ortofoto',
         url='https://ortos.dgterritorio.gov.pt/wcs/ortos2021', capas='Ortos2021_RGB', attribution='© DGT Portugal'),
    dict(nombre='SNIG Cartografía (WMS)', pais='🇵🇹 Portugal', tipo='WMS', categoria='Topográfico',
         url='https://mapas.dgterritorio.gov.pt/wms/ortos2018', capas='Ortos2018_RGB', attribution='© DGT / SNIG'),
    dict(nombre='Géoportail IGN France (WMTS)', pais='🇫🇷 Francia', tipo='WMTS', categoria='Topográfico',
         url='https://wxs.ign.fr/decouverte/geoportail/wmts?REQUEST=GetTile&SERVICE=WMTS&VERSION=1.0.0&TILEMATRIXSET=PM&LAYER=GEOGRAPHICALGRIDSYSTEMS.MAPS&STYLE=normal&FORMAT=image/png&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
         attribution='© IGN France'),
    dict(nombre='Orthofotos France (WMTS)', pais='🇫🇷 Francia', tipo='WMTS', categoria='Ortofoto',
         url='https://wxs.ign.fr/decouverte/geoportail/wmts?REQUEST=GetTile&SERVICE=WMTS&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&TILEMATRIXSET=PM&FORMAT=image/jpeg&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
         attribution='© IGN France'),
    dict(nombre='BRGM Géologie (WMS)', pais='🇫🇷 Francia', tipo='WMS', categoria='Geología',
         url='https://geoservices.brgm.fr/geologie', capas='GEOLOGIE', attribution='© BRGM France'),
    dict(nombre='BKG TopPlusOpen (WMTS)', pais='🇩🇪 Alemania', tipo='WMTS', categoria='Topográfico',
         url='https://sgx.geodatenzentrum.de/wmts_topplus_open/tile/1.0.0/web/default/WEBMERCATOR/{z}/{y}/{x}.png',
         attribution='© BKG (2023), dl-de/by-2-0'),
    dict(nombre='BKG Grau (WMTS)', pais='🇩🇪 Alemania', tipo='WMTS', categoria='Base',
         url='https://sgx.geodatenzentrum.de/wmts_topplus_open/tile/1.0.0/web_grau/default/WEBMERCATOR/{z}/{y}/{x}.png',
         attribution='© BKG (2023)'),
    dict(nombre='PCN Geoportale (WMS)', pais='🇮🇹 Italia', tipo='WMS', categoria='Topográfico',
         url='https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php', capas='CP.CadastralParcel', attribution='© Agenzia Entrate'),
    dict(nombre='IGM (WMS)', pais='🇮🇹 Italia', tipo='WMS', categoria='Topográfico',
         url='https://wms.igmi.org/wmss', capas='IGMI.BASEMAP', attribution='© IGM Italia'),
    dict(nombre='USGS Topo (WMTS)', pais='🇺🇸 EE.UU.', tipo='WMTS', categoria='Topográfico',
         url='https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',
         attribution='© USGS'),
    dict(nombre='USGS Imagery (WMTS)', pais='🇺🇸 EE.UU.', tipo='WMTS', categoria='Ortofoto',
         url='https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile/{z}/{y}/{x}',
         attribution='© USGS'),
    dict(nombre='Esri World Imagery (WMTS)', pais='🌍 Global', tipo='WMTS', categoria='Satélite',
         url='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
         attribution='© Esri'),
    dict(nombre='OpenTopoMap (WMTS)', pais='🌍 Global', tipo='WMTS', categoria='Topográfico',
         url='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', attribution='© OpenTopoMap'),
    dict(nombre='CartoDB Dark Matter (WMTS)', pais='🌍 Global', tipo='WMTS', categoria='Base',
         url='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', attribution='© CartoDB'),
    dict(nombre='GEBCO Batimetría (WMS)', pais='🌊 Océanos', tipo='WMS', categoria='Batimetría',
         url='https://www.gebco.net/data_and_products/gebco_web_services/web_map_service/mapserv',
         capas='GEBCO_LATEST_2', attribution='© GEBCO'),
    dict(nombre='David Rumsey (WMS)', pais='📜 Histórico', tipo='WMS', categoria='Histórico',
         url='https://maps.georeferencer.com/georeferences/835016264845361/2021-02-17T14:26:58.906506Z/wms',
         capas='0', attribution='© David Rumsey / Georeferencer'),
    
    # --- NUEVOS SERVICIOS DE ALTO VALOR ---
    dict(nombre='NASA GIBS Blue Marble (WMTS)', pais='🌍 Global', tipo='WMTS', categoria='Satélite',
         url='https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/EPSG3857_500m/{z}/{y}/{x}.jpeg',
         attribution='© NASA Global Imagery Browse Services (GIBS)'),
    dict(nombre='NASA Earth At Night (WMTS)', pais='🌍 Global', tipo='WMTS', categoria='Satélite',
         url='https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_CityLights_2012/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg',
         attribution='© NASA Earth Observatory'),
    dict(nombre='Copernicus Global Land Cover (WMS)', pais='🌍 Global', tipo='WMS', categoria='Usos del Suelo',
         url='https://services.terrascope.be/wms/v2', capas='WORLDCOVER_2020_MAP', attribution='© ESA WorldCover project / Copernicus'),
    dict(nombre='NOAA Weather/Radar (WMS)', pais='🌍 Global', tipo='WMS', categoria='Clima',
         url='https://nowcoast.noaa.gov/geoserver/observations/weather_radar/wms', capas='conus_base_reflectivity_mosaic', attribution='© NOAA'),
    
    dict(nombre='BKG Topo Open (WMS)', pais='🇩🇪 Alemania', tipo='WMS', categoria='Topográfico',
         url='https://sgx.geodatenzentrum.de/wms_topplus_open', capas='web', attribution='© BKG Alemania'),
         
    dict(nombre='Swisstopo Pixelkarte (WMTS)', pais='🇨🇭 Suiza', tipo='WMTS', categoria='Topográfico',
         url='https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg',
         attribution='© Swisstopo'),
    dict(nombre='Swisstopo Satélite (WMTS)', pais='🇨🇭 Suiza', tipo='WMTS', categoria='Satélite',
         url='https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg',
         attribution='© Swisstopo'),
         
    dict(nombre='OSM Standard (WMTS)', pais='🌍 Global', tipo='WMTS', categoria='Base',
         url='https://tile.openstreetmap.org/{z}/{x}/{y}.png', attribution='© OpenStreetMap contributors'),
    dict(nombre='OSM Humanitarian (WMTS)', pais='🌍 Global', tipo='WMTS', categoria='Base',
         url='https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', attribution='© HOT OSM'),
         
    dict(nombre='IDE Canarias GRAFCAN (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Regional',
         url='https://idecan2.grafcan.es/ServicioWMS/OrtoExpress', capas='OrtoExpress', attribution='© GRAFCAN Gobierno de Canarias'),
    dict(nombre='IDE Euskadi GeoEuskadi (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Regional',
         url='https://www.geo.euskadi.eus/WMS_ORTOARGAZKIAK', capas='ORTO_ACTUAL', attribution='© GeoEuskadi'),
    dict(nombre='IDE Galicia IET (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Regional',
         url='https://ideg.xunta.gal/servicios/wms/ortofotos', capas='Ortofoto_Mas_Actual', attribution='© IET Xunta de Galicia'),
         
    dict(nombre='AEMET Radar Nacional (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Clima',
         url='https://wms.mapama.gob.es/sig/Agua/Radares/wms.aspx', capas='Radares_AEMET', attribution='© AEMET / MAPAMA'),
    dict(nombre='Confederación Hidrográfica Ebro (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Hidrografía',
         url='https://idebro.chebro.es/geoserver/wms', capas='idebro:RedDrenaje', attribution='© CH Ebro'),
    dict(nombre='IGME Mapa Geológico (WMS)', pais='🇪🇸 España', tipo='WMS', categoria='Geología',
         url='https://mapas.igme.es/gis/services/Cartografia_Geologica/IGME_MAGNA_50/MapServer/WMSServer', capas='0', attribution='© IGME'),
         
    dict(nombre='IGN Argentina (WMTS)', pais='🇦🇷 Argentina', tipo='WMTS', categoria='Topográfico',
         url='https://wms.ign.gob.ar/geoserver/gwc/service/wmts?layer=capabaseargenmapa&style=&tilematrixset=EPSG:3857&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image/png&TileMatrix=EPSG:3857:{z}&TileCol={x}&TileRow={y}', attribution='© IGN Argentina'),
    dict(nombre='IDE Chile MBN (WMS)', pais='🇨🇱 Chile', tipo='WMS', categoria='Base',
         url='https://ide.minbienes.cl/geoserver/wms', capas='Bienes:Lotes', attribution='© IDE Chile'),
    dict(nombre='IBGE Mapa Topográfico (WMS)', pais='🇧🇷 Brasil', tipo='WMS', categoria='Topográfico',
         url='https://geoservicos.ibge.gov.br/geoserver/ows', capas='CCAR:BC250_Ed_Atual_topografico', attribution='© IBGE Brasil'),
]


def seed():
    with app.app_context():
        # Crear tabla si no existe
        db.create_all()
        print("✅ Tabla servicios_ide creada/verificada.")

        added = 0
        skipped = 0
        for s in CATALOGO_INICIAL:
            existing = ServicioIDE.query.filter_by(
                url=s['url'],
                tipo=s['tipo'],
                capas=s.get('capas')
            ).first()
            if existing:
                skipped += 1
                continue
            srv = ServicioIDE(
                nombre=s['nombre'],
                tipo=s['tipo'],
                url=s['url'],
                capas=s.get('capas'),
                attribution=s.get('attribution', ''),
                pais=s.get('pais', ''),
                categoria=s.get('categoria', ''),
                opacidad=0.85,
                creado_por=None,
            )
            db.session.add(srv)
            added += 1

        db.session.commit()
        print(f"✅ Seeding completado: {added} servicios añadidos, {skipped} ya existentes.")


if __name__ == '__main__':
    seed()
