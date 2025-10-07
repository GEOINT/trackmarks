
from dataclasses import dataclass
from datetime import datetime
from trackmarks.core.spatial import Ellipse

@dataclass
class PlotSource():
    
    system: str
    version: int
    
@dataclass
class DurableSource(PlotSource):
    
    identifier: str
    

@dataclass
class Plot():
    
    location: Ellipse
    first_observed: datetime
    last_observed: datetime
    source: PlotSource
    
