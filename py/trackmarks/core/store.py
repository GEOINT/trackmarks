
from abc import ABC, abstractmethod
from typing import Set, Iterable
from dataclasses import dataclass, field
from shapely import geometry
from datetime import datetime
from trackmarks.core.track import Trackable, DurableIdentifier, \
    DurableTrackable, TransientTrackable

class TrackStore(ABC):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @abstractmethod
    def create(self, trackable: Trackable) -> Trackable:
        raise NotImplementedError()
       
    @abstractmethod    
    def new_durable_track(self, identifiers: Set[DurableIdentifier]) \
        -> DurableTrackable:
        raise NotImplementedError()
       
    @abstractmethod    
    def new_transient_track(self) -> TransientTrackable:
        raise NotImplementedError()
        
    @abstractmethod
    def get_durable_tracks(self, identifiers: Set[DurableIdentifier] = None,
                           aoi: geometry.Polygon = None,
                           after: datetime = None,
                           before: datetime = None) -> Iterable[DurableTrackable]:
        raise NotImplementedError()
    
    @abstractmethod
    def get_transient_tracks(self, aoi: geometry.Polygon = None,
                             after: datetime = None,
                             before: datetime = None) \
        -> Iterable[TransientTrackable]:
        raise NotImplementedError()