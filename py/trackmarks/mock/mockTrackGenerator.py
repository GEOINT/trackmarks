import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from skmob.core.trajectorydataframe import TrajDataFrame
import random

class VehicleTrajectoryGenerator:
    """
    Generate mock vehicle trackable plot data based on OSM road networks.
    """
    
    def __init__(self, place_name=None, graph=None):
        """
        Initialize with either a place name or existing graph.
        
        Args:
            place_name: Name of place to download OSM data for (e.g., "Manhattan, New York, USA")
            graph: Pre-loaded OSMnx graph (optional)
        """
        if graph is not None:
            self.G = graph
        elif place_name is not None:
            print(f"Downloading OSM data for {place_name}...")
            self.G = ox.graph_from_place(place_name, network_type='drive')
        else:
            raise ValueError("Either place_name or graph must be provided")
        
        # Project graph to UTM for accurate distance calculations
        self.G_proj = ox.project_graph(self.G)
    
    def get_nearest_node(self, lat, lon):
        """Find nearest node in graph to given coordinates."""
        return ox.distance.nearest_nodes(self.G, lon, lat)
    
    def generate_trajectories(self, 
                            origin_coords,
                            dest_coords,
                            num_vehicles=5,
                            min_velocity=20,
                            max_velocity=60,
                            departure_time="2024-01-01 08:00:00",
                            max_travel_duration=120,
                            rest_duration=15,
                            sample_interval=60):
        """
        Generate vehicle trajectories based on user-defined criteria.
        
        Args:
            origin_coords: Tuple of (latitude, longitude) for origin
            dest_coords: Tuple of (latitude, longitude) for destination
            num_vehicles: Number of unique trackable vehicles
            min_velocity: Minimum velocity in km/h
            max_velocity: Maximum velocity in km/h
            departure_time: Departure time as string "YYYY-MM-DD HH:MM:SS"
            max_travel_duration: Maximum travel duration before rest/stop (minutes)
            rest_duration: Rest/stop duration (minutes)
            sample_interval: Time between GPS samples (seconds)
        
        Returns:
            TrajDataFrame: Trajectory data frame with all vehicle tracks
        """
        
        # Convert departure time to datetime
        base_time = datetime.strptime(departure_time, "%Y-%m-%d %H:%M:%S")
        
        # Find nearest nodes for origin and destination
        origin_node = self.get_nearest_node(origin_coords[0], origin_coords[1])
        dest_node = self.get_nearest_node(dest_coords[0], dest_coords[1])
        
        print(f"Origin node: {origin_node}")
        print(f"Destination node: {dest_node}")
        
        # Calculate shortest path
        try:
            path = nx.shortest_path(self.G, origin_node, dest_node, weight='length')
            print(f"Path found with {len(path)} nodes")
        except nx.NetworkXNoPath:
            print("No path found between origin and destination!")
            return None
        
        # Calculate path distances
        path_distances = self._calculate_path_distances(path)
        total_distance = path_distances[-1]
        
        print(f"Total route distance: {total_distance/1000:.2f} km")
        
        all_trajectories = []
        
        # Generate trajectories for each vehicle
        for vehicle_id in range(1, num_vehicles + 1):
            print(f"\nGenerating trajectory for vehicle {vehicle_id}...")
            
            # Random velocity for this vehicle (km/h)
            vehicle_velocity = random.uniform(min_velocity, max_velocity)
            
            # Stagger departure times slightly
            vehicle_departure = base_time + timedelta(minutes=random.randint(0, 30))
            
            trajectory = self._generate_single_trajectory(
                vehicle_id=vehicle_id,
                path=path,
                path_distances=path_distances,
                velocity=vehicle_velocity,
                departure_time=vehicle_departure,
                max_travel_duration=max_travel_duration,
                rest_duration=rest_duration,
                sample_interval=sample_interval
            )
            
            all_trajectories.append(trajectory)
        
        # Combine all trajectories
        combined_df = pd.concat(all_trajectories, ignore_index=True)
        
        # Create TrajDataFrame
        tdf = TrajDataFrame(combined_df, 
                           latitude='lat', 
                           longitude='lng', 
                           datetime='datetime', 
                           user_id='vehicle_id')
        
        print(f"\nGenerated {len(combined_df)} GPS points for {num_vehicles} vehicles")
        
        return tdf
    
    def _calculate_path_distances(self, path):
        """Calculate cumulative distances along path."""
        distances = [0]
        for i in range(len(path) - 1):
            edge_data = self.G[path[i]][path[i + 1]][0]
            distances.append(distances[-1] + edge_data['length'])
        return distances
    
    def _generate_single_trajectory(self, vehicle_id, path, path_distances, 
                                   velocity, departure_time, max_travel_duration,
                                   rest_duration, sample_interval):
        """Generate trajectory for a single vehicle."""
        
        records = []
        current_time = departure_time
        velocity_ms = velocity / 3.6  # Convert km/h to m/s
        
        current_distance = 0
        total_distance = path_distances[-1]
        travel_time_minutes = 0
        
        while current_distance < total_distance:
            # Check if vehicle needs rest
            if travel_time_minutes >= max_travel_duration:
                # Add rest period
                current_time += timedelta(minutes=rest_duration)
                travel_time_minutes = 0
                print(f"  Vehicle {vehicle_id} resting at {current_distance/1000:.2f} km")
            
            # Find current position on path
            node_idx = np.searchsorted(path_distances, current_distance)
            if node_idx >= len(path):
                node_idx = len(path) - 1
            
            # Interpolate position between nodes
            if node_idx > 0 and node_idx < len(path):
                prev_dist = path_distances[node_idx - 1]
                next_dist = path_distances[node_idx]
                ratio = (current_distance - prev_dist) / (next_dist - prev_dist) if next_dist > prev_dist else 0
                
                prev_node = path[node_idx - 1]
                next_node = path[node_idx]
                
                prev_lat = self.G.nodes[prev_node]['y']
                prev_lon = self.G.nodes[prev_node]['x']
                next_lat = self.G.nodes[next_node]['y']
                next_lon = self.G.nodes[next_node]['x']
                
                lat = prev_lat + ratio * (next_lat - prev_lat)
                lon = prev_lon + ratio * (next_lon - prev_lon)
            else:
                # Use exact node position
                node = path[node_idx]
                lat = self.G.nodes[node]['y']
                lon = self.G.nodes[node]['x']
            
            # Add some GPS noise (realistic variation)
            lat += random.gauss(0, 0.00001)
            lon += random.gauss(0, 0.00001)
            
            # Add velocity variation (traffic, acceleration, etc.)
            velocity_variation = random.uniform(0.7, 1.3)
            actual_velocity = velocity_ms * velocity_variation
            
            records.append({
                'vehicle_id': vehicle_id,
                'lat': lat,
                'lng': lon,
                'datetime': current_time,
                'velocity_kmh': actual_velocity * 3.6
            })
            
            # Move to next sample
            distance_increment = actual_velocity * sample_interval
            current_distance += distance_increment
            current_time += timedelta(seconds=sample_interval)
            travel_time_minutes += sample_interval / 60
        
        # Ensure final destination is included
        dest_node = path[-1]
        records.append({
            'vehicle_id': vehicle_id,
            'lat': self.G.nodes[dest_node]['y'],
            'lng': self.G.nodes[dest_node]['x'],
            'datetime': current_time,
            'velocity_kmh': 0
        })
        
        return pd.DataFrame(records)


# Example usage
if __name__ == "__main__":
    # Configuration parameters
    CONFIG = {
        'place_name': "Piedmont, Atlanta, Georgia, USA",
        'origin_coords': (33.7902, -84.3880),  # Near Piedmont Park
        'dest_coords': (33.7490, -84.3880),    # Midtown Atlanta
        'num_vehicles': 3,
        'min_velocity': 25,  # km/h
        'max_velocity': 55,  # km/h
        'departure_time': "2024-01-15 08:00:00",
        'max_travel_duration': 45,  # minutes before rest
        'rest_duration': 10,  # minutes
        'sample_interval': 30  # seconds between GPS samples
    }
    
    # Initialize generator
    generator = VehicleTrajectoryGenerator(place_name=CONFIG['place_name'])
    
    # Generate trajectories
    trajectories = generator.generate_trajectories(
        origin_coords=CONFIG['origin_coords'],
        dest_coords=CONFIG['dest_coords'],
        num_vehicles=CONFIG['num_vehicles'],
        min_velocity=CONFIG['min_velocity'],
        max_velocity=CONFIG['max_velocity'],
        departure_time=CONFIG['departure_time'],
        max_travel_duration=CONFIG['max_travel_duration'],
        rest_duration=CONFIG['rest_duration'],
        sample_interval=CONFIG['sample_interval']
    )
    
    # Display results
    if trajectories is not None:
        print("\n=== Trajectory Summary ===")
        print(trajectories.head(20))
        print(f"\nShape: {trajectories.shape}")
        print(f"Vehicles: {trajectories['uid'].nunique()}")
        print(f"Time range: {trajectories['datetime'].min()} to {trajectories['datetime'].max()}")
        
        # Optional: Save to CSV
        trajectories.to_csv('vehicle_trajectories.csv', index=False)
        print("\nTrajectories saved to 'vehicle_trajectories.csv'")
        
        # Optional: Plot trajectories
        try:
            trajectories.plot_trajectory(zoom=12, weight=3, opacity=0.7)
            print("Trajectory map generated!")
        except Exception as e:
            print(f"Note: Map plotting requires additional setup: {e}")