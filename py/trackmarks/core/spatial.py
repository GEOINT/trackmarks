from __future__ import annotations
from typing import Optional, Callable, Any, Annotated, Union, Tuple, \
    Generic, TypeVar
from dataclasses import dataclass, field
from shapely import geometry
import shapely.affinity
from shapely.ops import transform
from trackmarks.core.lazy import LazyProperty
from trackmarks.core import unit_reg
from pint.registry import Quantity
import pyproj
import logging
import geopandas as gpd

logger = logging.Logger(name='trackmarks')

Distance = Annotated[Quantity, 'Distance']
G = TypeVar('G', bound=geometry.base.BaseGeometry)

DEFAULT_ELLIPSE_RESOLUTION = 8
DEFAULT_ELLIPSE_ORIENTATION = 0.0
DEFAULT_EPSG_CRS = 4326

@dataclass
class Ellipse():
    
    centroid: geometry.Point #ESPG:4326 @TODO check/normalize on init
    semi_major: float #nautical miles
    semi_minor: float #nautical miles
    orientation: float = field(default=DEFAULT_ELLIPSE_ORIENTATION)
    
    #lazily computed
    _ellipse: Optional[geometry.Polygon] = field(default=None, 
                                                 init=False, 
                                                 repr=False)
    @property
    def ellipse(self) -> geometry.Polygon:
        #lazily_computed
        if self._ellipse is None:
            self.generate_ellipse(cache=True)
        return self._ellipse
    
    def generate_ellipse(self, resolution: float = DEFAULT_ELLIPSE_RESOLUTION,
                         cache: bool = False) -> geometry.Polygon:
        reprojector = OptimalReprojector(input_epsg=DEFAULT_EPSG_CRS)
        ellipse = reprojector.apply_geometry(self.centroid, 
                                          func=Ellipse._generate_utm_ellipse,
                                          semi_major=self.semi_major,
                                          semi_minor=self.semi_minor,
                                          orientation=self.orientation,
                                          resolution=resolution)
        if cache:
            self._ellipse = ellipse
        return ellipse
        
    @staticmethod
    def _generate_utm_ellipse(centroid: geometry.Point, #utm
                         semi_major: Distance, 
                         semi_minor: Distance, 
                         orientation: float = DEFAULT_ELLIPSE_ORIENTATION,
                         resolution: float = DEFAULT_ELLIPSE_RESOLUTION) \
        -> geometry.Polygon:
            
        major_meters = semi_major.to(unit_reg.meter).magnitude
        minor_meters = semi_minor.to(unit_reg.meter).magnitude
        ellipse = shapely.affinity.scale(centroid.buffer(1,resolution=resolution), 
                                         xfact=major_meters, 
                                         yfact=minor_meters)
        return ellipse if orientation == DEFAULT_ELLIPSE_ORIENTATION \
            else shapely.affinity.rotate(ellipse, orientation)
            
   

class OptimalReprojector:

    def __init__(self, input_epsg: int = DEFAULT_EPSG_CRS):
        self.input_crs = pyproj.CRS.from_epsg(input_epsg)

    def _determine_optimal_crs(self, point_4326: geometry.Point) -> pyproj.CRS:
        """
        Internal method to determine an 'optimal' local CRS.
        
        This implementation uses a simple logic: it checks the latitude and 
        prefers a globally recognized equal-area projection or a UTM zone.
        For simplicity and general applicability, we'll favor the *UTM* zone for points that aren't too far north or south, as it's common 
        for local distance calculations.
        
        For a more advanced equal-area projection, a *Lambert Azimuthal 
        Equal Area (LAEA)* or a *custom Albers* might be chosen.
        """
        lon = point_4326.x
        lat = point_4326.y

        # UTM zones are generally good for local, low-distortion planar
        # calculations, though they are not equal-area. UTM is a common 
        # *practical* 'optimal' choice for local distance/area.
        # pyproj makes it easy to find the appropriate UTM CRS.
        if -80 < lat < 84:
            # Find the best UTM zone for the location
            utm_crs = pyproj.CRS.from_string(f"+proj=utm +zone={int((lon + 180) / 6) + 1} +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
            return utm_crs
        else:
            # For polar regions, use a suitable polar stereographic or
            # a standard continental Equal Area projection.
            # Using World Azimuthal Equidistant for simplicity in edge cases.
            return pyproj.CRS.from_epsg(54032) # World Azimuthal Equidistant

    def _is_geometry_within_crs_bounds(geometry: geometry.base.BaseGeometry, 
                                      crs: pyproj.CRS):
    
        # Get the bounds of the CRS (min_lon, max_lon, min_lat, max_lat)
        bounds = crs.area_of_use.bounds
        min_lon, min_lat, max_lon, max_lat = bounds

        # Check if the geometry is within the bounds
        return (
            min_lon <= geometry.x <= max_lon and
            min_lat <= geometry.y <= max_lat
        )
        
    
    def get_optimal_transformers(self, geom: geometry.base.Geometry) \
        -> Tuple[pyproj.Transformer,pyproj.Transformer]:
        
        #TODO determine if caching resolve transformers can optimize
        optimal_crs = self._determine_optimal_crs(geom if isinstance(geom, geometry.Point) else geom.centroid)

        if optimal_crs == self.input_crs:
            return None

        to_transformer = pyproj.Transformer.from_crs(
            self.input_crs, 
            optimal_crs, 
            always_xy=True
        )
        
        return_transformer = pyproj.Transformer.from_crs(
            optimal_crs, 
            self.input_crs, 
            always_xy=True
        )
        
        return (to_transformer, return_transformer)
    
    def apply_geometry(self, geom: G, func: Callable[G], *args, **kwargs) \
        -> geometry.base.BaseGeometry:
            
        to_transformer, return_transformer = self.get_optimal_transformers(geom)
        
        transformed_geom = transform(to_transformer.transform, geom)
        transformed_geom = func(transformed_geom, *args, **kwargs)
        return transform(return_transformer.transform, transformed_geom)
    
    def apply_geodataframe(self, gdf: gpd.GeoDataFrame, func: Callable[G], *args, **kwargs) \
        -> gpd.GeoDataFrame:
        gdf['geometry'] = gdf.apply(lambda x: self.apply_geometry(x.geometry, \
                                                                  func, \
                                                                      *args, \
                                                                          **kwargs), axis=1)
        return gdf
    