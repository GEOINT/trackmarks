import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

class ShortestPathGenerator:
    """
    Generate shortest distance graph using OSM roads between origin and destination.
    """
    
    def __init__(self, place_name=None, bbox=None, distance=None, center_point=None):
        """
        Initialize by downloading OSM data.
        
        Args:
            place_name: Name of place (e.g., "Manhattan, New York, USA")
            bbox: Bounding box as (north, south, east, west)
            distance: Distance in meters from center_point to download
            center_point: Tuple of (lat, lon) for distance-based download
        """
        if place_name:
            print(f"Downloading OSM data for {place_name}...")
            self.G = ox.graph_from_place(place_name, network_type='drive')
        elif bbox:
            print(f"Downloading OSM data for bounding box...")
            self.G = ox.graph_from_bbox(bbox=bbox, network_type='drive')
        elif distance and center_point:
            print(f"Downloading OSM data within {distance}m of {center_point}...")
            self.G = ox.graph_from_point(center_point, dist=distance, network_type='drive')
        else:
            raise ValueError("Must provide place_name, bbox, or (distance and center_point)")
        
        print(f"Graph loaded: {len(self.G.nodes)} nodes, {len(self.G.edges)} edges")
    
    def get_nearest_node(self, lat, lon):
        """Find nearest node in graph to given coordinates."""
        node = ox.distance.nearest_nodes(self.G, lon, lat)
        node_data = self.G.nodes[node]
        print(f"Nearest node to ({lat}, {lon}): {node} at ({node_data['y']:.6f}, {node_data['x']:.6f})")
        return node
    
    def calculate_shortest_path(self, origin_coords, dest_coords, weight='length'):
        """
        Calculate shortest path between origin and destination.
        
        Args:
            origin_coords: Tuple of (latitude, longitude) for origin
            dest_coords: Tuple of (latitude, longitude) for destination
            weight: Edge weight to minimize ('length' for distance, 'travel_time' for time)
        
        Returns:
            dict: Contains path nodes, edges, distance, and other metrics
        """
        print("\n=== Calculating Shortest Path ===")
        
        # Find nearest nodes
        origin_node = self.get_nearest_node(origin_coords[0], origin_coords[1])
        dest_node = self.get_nearest_node(dest_coords[0], dest_coords[1])
        
        # Calculate shortest path
        try:
            route = nx.shortest_path(self.G, origin_node, dest_node, weight=weight)
            print(f"\nPath found with {len(route)} nodes")
        except nx.NetworkXNoPath:
            print("ERROR: No path found between origin and destination!")
            return None
        
        # Calculate path metrics
        path_length = sum(
            self.G[route[i]][route[i + 1]][0]['length'] 
            for i in range(len(route) - 1)
        )
        
        # Get path edges for visualization
        route_edges = [(route[i], route[i + 1]) for i in range(len(route) - 1)]
        
        # Calculate additional metrics
        path_coords = [(self.G.nodes[node]['y'], self.G.nodes[node]['x']) for node in route]
        
        results = {
            'origin_node': origin_node,
            'dest_node': dest_node,
            'origin_coords': origin_coords,
            'dest_coords': dest_coords,
            'route_nodes': route,
            'route_edges': route_edges,
            'route_coords': path_coords,
            'distance_meters': path_length,
            'distance_km': path_length / 1000,
            'num_nodes': len(route),
            'num_edges': len(route_edges)
        }
        
        print(f"\n=== Path Statistics ===")
        print(f"Distance: {results['distance_km']:.2f} km ({results['distance_meters']:.0f} m)")
        print(f"Nodes in path: {results['num_nodes']}")
        print(f"Edges in path: {results['num_edges']}")
        
        return results
    
    def plot_shortest_path(self, path_results, figsize=(12, 12), 
                          node_size=50, route_linewidth=4, 
                          save_path=None):
        """
        Visualize the shortest path on the road network.
        
        Args:
            path_results: Results dictionary from calculate_shortest_path()
            figsize: Figure size tuple
            node_size: Size of origin/destination markers
            route_linewidth: Width of route line
            save_path: Optional path to save the figure
        """
        if path_results is None:
            print("No path to plot!")
            return
        
        print("\n=== Generating Visualization ===")
        
        # Create figure
        fig, ax = ox.plot_graph(
            self.G, 
            figsize=figsize,
            node_size=0,
            edge_linewidth=0.5,
            edge_color='#CCCCCC',
            bgcolor='white',
            show=False,
            close=False
        )
        
        # Plot the shortest path route
        ox.plot_graph_route(
            self.G,
            path_results['route_nodes'],
            route_linewidth=route_linewidth,
            node_size=0,
            bgcolor='white',
            orig_dest_size=node_size * 3,
            route_color='#FF0000',
            route_alpha=0.7,
            ax=ax,
            show=False,
            close=False
        )
        
        # Add origin and destination markers
        origin_node = path_results['origin_node']
        dest_node = path_results['dest_node']
        
        ax.scatter(
            self.G.nodes[origin_node]['x'], 
            self.G.nodes[origin_node]['y'],
            c='green', s=node_size * 6, marker='o', 
            zorder=5, edgecolors='black', linewidths=2,
            label='Origin'
        )
        
        ax.scatter(
            self.G.nodes[dest_node]['x'], 
            self.G.nodes[dest_node]['y'],
            c='red', s=node_size * 6, marker='s', 
            zorder=5, edgecolors='black', linewidths=2,
            label='Destination'
        )
        
        # Add title and legend
        ax.set_title(
            f"Shortest Path: {path_results['distance_km']:.2f} km\n"
            f"Origin: {path_results['origin_coords']} → Destination: {path_results['dest_coords']}",
            fontsize=12, fontweight='bold', pad=20
        )
        
        # Create custom legend
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='green', 
                   markersize=10, markeredgecolor='black', markeredgewidth=2, label='Origin'),
            Line2D([0], [0], marker='s', color='w', markerfacecolor='red', 
                   markersize=10, markeredgecolor='black', markeredgewidth=2, label='Destination'),
            Line2D([0], [0], color='red', linewidth=3, alpha=0.7, label='Shortest Path')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Figure saved to: {save_path}")
        
        plt.show()
        print("Visualization complete!")
    
    def get_route_details(self, path_results):
        """
        Get detailed information about each segment of the route.
        
        Args:
            path_results: Results dictionary from calculate_shortest_path()
        
        Returns:
            list: Detailed information for each route segment
        """
        if path_results is None:
            return None
        
        segments = []
        route = path_results['route_nodes']
        
        for i in range(len(route) - 1):
            edge = self.G[route[i]][route[i + 1]][0]
            
            segment = {
                'segment': i + 1,
                'from_node': route[i],
                'to_node': route[i + 1],
                'from_coords': (self.G.nodes[route[i]]['y'], self.G.nodes[route[i]]['x']),
                'to_coords': (self.G.nodes[route[i + 1]]['y'], self.G.nodes[route[i + 1]]['x']),
                'length_m': edge['length'],
                'length_km': edge['length'] / 1000,
                'street_name': edge.get('name', 'Unnamed'),
                'highway_type': edge.get('highway', 'Unknown')
            }
            segments.append(segment)
        
        return segments


# Example usage
if __name__ == "__main__":
    # User-provided coordinates
    ORIGIN = (33.7902, -84.3880)      # Example: Near Piedmont Park, Atlanta
    DESTINATION = (33.7490, -84.3880)  # Example: Midtown Atlanta
    
    # Method 1: Use place name
    print("=== Method 1: Using Place Name ===")
    path_gen = ShortestPathGenerator(place_name="Piedmont, Atlanta, Georgia, USA")
    
    # Calculate shortest path
    results = path_gen.calculate_shortest_path(ORIGIN, DESTINATION)
    
    # Plot the path
    if results:
        path_gen.plot_shortest_path(results, save_path='shortest_path.png')
        
        # Get detailed route information
        segments = path_gen.get_route_details(results)
        
        print("\n=== Route Segments ===")
        for seg in segments[:5]:  # Show first 5 segments
            print(f"Segment {seg['segment']}: {seg['street_name']} "
                  f"({seg['length_m']:.0f}m) - {seg['highway_type']}")
    
    # Method 2: Use distance from center point
    print("\n\n=== Method 2: Using Distance from Center ===")
    center = ((ORIGIN[0] + DESTINATION[0]) / 2, (ORIGIN[1] + DESTINATION[1]) / 2)
    path_gen2 = ShortestPathGenerator(center_point=center, distance=5000)
    
    results2 = path_gen2.calculate_shortest_path(ORIGIN, DESTINATION)
    if results2:
        path_gen2.plot_shortest_path(results2)
    
    # Method 3: Use bounding box
    print("\n\n=== Method 3: Using Bounding Box ===")
    # Create bounding box around origin and destination
    north = max(ORIGIN[0], DESTINATION[0]) + 0.01
    south = min(ORIGIN[0], DESTINATION[0]) - 0.01
    east = max(ORIGIN[1], DESTINATION[1]) + 0.01
    west = min(ORIGIN[1], DESTINATION[1]) - 0.01
    
    path_gen3 = ShortestPathGenerator(bbox=(north, south, east, west))
    results3 = path_gen3.calculate_shortest_path(ORIGIN, DESTINATION)
    if results3:
        path_gen3.plot_shortest_path(results3)