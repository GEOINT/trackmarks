import unittest
from trackmarks.core import unit_reg
from trackmarks.core.spatial import Ellipse, OptimalReprojector
from shapely import geometry
from shapely.ops import transform

class EllipseLazyTest(unittest.TestCase):
    
    def setUp(self):
        self.centroid_4326 = geometry.Point(-84.39, 33.75)
        proj = OptimalReprojector()
        to_trans, from_trans = proj.get_optimal_transformers(self.centroid_4326)
        self.centroid_utm = transform(to_trans.transform, self.centroid_4326)
        self.ellipse = Ellipse(centroid=self.centroid_4326,
                               semi_major=2* unit_reg.nautical_mile,
                               semi_minor=1* unit_reg.nautical_mile, 
                               orientation=10)
        
        
    def test_lazy_caching(self):

        print(f'{self.ellipse.ellipse})')

    
    # def test_ellipse_generation(self):
    #     print(Ellipse._generate_utm_ellipse(centroid=self.centroid_utm,
    #                            semi_major=2 * unit_reg.nautical_mile, 
    #                            semi_minor=1 * unit_reg.nautical_mile, 
    #                            orientation=10))

if __name__ == '__main__':
    unittest.main() 
        
