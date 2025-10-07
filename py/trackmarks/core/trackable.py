# -*- coding: utf-8 -*-
"""
Created on Mon Oct  6 08:58:59 2025

@author: smsie
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Set
import uuid
from datetime import datetime
import geopandas as gpd
from trackable.core.spatial import Ellipse
from trackable.core.track import Plot

    
@dataclass
class Trackable(ABC):
    
    first_observed: datetime
    last_observed: datetime
    last_known_position: Ellipse
    _guid: str = field(default_factory=uuid.uuid4)
    
    @abstractmethod
    def get_plots(self, after: datetime = None, 
                  before: datetime = None) -> TrackHistory:
        raise NotImplementedError()
        
    # def get_activities(self, after: datetime, before: datetime) -> gpd.GeoDataFrame:
    #     raise NotImplementedError()

class TrackHistory(ABC):
    
    def __init__(self, after: datetime = None, before: datetime = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.after = after
        self.before = before
    
    @abstractmethod
    def __iter__(self) -> Plot:
        raise NotImplementedError()
        
    @abstractmethod
    def as_gdf(self) -> gpd.GeoDataFrame:
        raise NotImplementedError()
        
@dataclass
class DurableIdentifier():
    identifier: str
    system: str
     
@dataclass
class DurableTrackable(Trackable):
    
    identifiers: Set[DurableIdentifier] = field(default_factory=set)

@dataclass        
class TransientTrackable(Trackable):
    pass
        
