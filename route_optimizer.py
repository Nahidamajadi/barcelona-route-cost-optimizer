import osmnx as ox
import networkx as nx
import pandas as pd
import duckdb
import matplotlib.pyplot as plt


# 1. BUILD BARCELONA ROAD NETWORK


def build_barcelona_graph():

    print("1. Downloading Barcelona road network from OpenStreetMap...")

    graph = ox.graph_from_place(
        "Barcelona, Spain",
        network_type="drive"
    )

    # Add estimated road speeds
    graph = ox.routing.add_edge_speeds(graph)

    # Add estimated travel times
    graph = ox.routing.add_edge_travel_times(graph)

    print("Barcelona road network ready.")

    return graph



# 2. CALCULATE OPERATIONAL COST FOR EVERY ROAD

def calculate_operational_costs(
    graph,
    fuel_rate=0.25,
    wage_rate=0.25
):

    print("2. Calculating operational cost for every road...")

    for u, v, key, data in graph.edges(
        keys=True,
        data=True
    ):

        # Distance
        length_m = data.get("length", 0.0)
        length_km = length_m / 1000.0

        # Travel time
        travel_time_sec = data.get("travel_time", 0.0)
        travel_time_min = travel_time_sec / 60.0

        # Cost calculations
        fuel_cost_eur = length_km * fuel_rate
        wage_cost_eur = travel_time_min * wage_rate

        total_cost_eur = (
            fuel_cost_eur
            + wage_cost_eur
        )

        # Store calculations on each road edge
        data["length_km"] = length_km
        data["travel_time_min"] = travel_time_min
        data["fuel_cost_eur"] = fuel_cost_eur
        data["wage_cost_eur"] = wage_cost_eur
        data["cost_eur"] = total_cost_eur

    print("Operational cost calculation complete.")

    return graph


# 3. CALCULATE ONE ROUTE STRATEGY


def calculate_route(
    graph,
    origin_node,
    destination_node,
    strategy,
    weight
):

    path = nx.shortest_path(
        graph,
        source=origin_node,
        target=destination_node,
        weight=weight,
        method="dijkstra"
    )

    route_edges = ox.routing.route_to_gdf(
        graph,
        path,
        weight=weight
    )

    result = {
        "strategy": strategy,
        "distance_km": route_edges["length_km"].sum(),
        "travel_time_min": route_edges["travel_time_min"].sum(),
        "fuel_cost_eur": route_edges["fuel_cost_eur"].sum(),
        "wage_cost_eur": route_edges["wage_cost_eur"].sum(),
        "total_cost_eur": route_edges["cost_eur"].sum()
    }

    return path, route_edges, result



# 4. COMPARE SHORTEST, FASTEST AND LOWEST-COST ROUTES


def compare_routes(
    graph,
    origin_coordinates,
    destination_coordinates
):

    origin_node = ox.distance.nearest_nodes(
        graph,
        X=origin_coordinates[1],
        Y=origin_coordinates[0]
    )

    destination_node = ox.distance.nearest_nodes(
        graph,
        X=destination_coordinates[1],
        Y=destination_coordinates[0]
    )

    strategies = {
        "shortest_distance": "length",
        "fastest_time": "travel_time",
        "lowest_cost": "cost_eur"
    }

    results = []
    routes = {}

    for strategy, weight in strategies.items():

        path, route_edges, result = calculate_route(
            graph,
            origin_node,
            destination_node,
            strategy,
            weight
        )

        results.append(result)

        routes[strategy] = {
            "path": path,
            "edges": route_edges
        }

    comparison_df = pd.DataFrame(results)

    return comparison_df, routes



# 5. RUN BARCELONA CASE STUDY


graph = build_barcelona_graph()

graph = calculate_operational_costs(
    graph,
    fuel_rate=0.25,
    wage_rate=0.25
)


# Plaça de Catalunya
origin = (
    41.3870,
    2.1700
)


# Sagrada Família
destination = (
    41.4036,
    2.1744
)


comparison_df, routes = compare_routes(
    graph,
    origin,
    destination
)


print("\nROUTE COMPARISON")
print("================")
print(comparison_df.round(2))


# 6. SAVE RESULTS TO DUCKDB


connection = duckdb.connect(
    "barcelona_routes.duckdb"
)

connection.execute("""
    CREATE OR REPLACE TABLE route_results AS
    SELECT *
    FROM comparison_df
""")


print("\nRoute results saved to DuckDB.")



# 7. VERIFY DUCKDB RESULTS


route_results = connection.execute("""
    SELECT *
    FROM route_results
""").df()


print("\nDUCKDB ROUTE RESULTS")
print("====================")
print(route_results)


connection.close()

# 8. Visualize shortest vs lowest-cost route

shortest_path = routes["shortest_distance"]["path"]
lowest_cost_path = routes["lowest_cost"]["path"]

fig, ax = ox.plot_graph_routes(
    graph,
    routes=[
        shortest_path,
        lowest_cost_path
    ],
    route_colors=[
        "blue",
        "red"
    ],
    route_linewidths=[
        4,
        4
    ],
    node_size=0,
    show=False,
    close=False
)

# 8. Visualize shortest vs lowest-cost route

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# 1. Path -> set of (u, v) edges
def path_to_edges(path):
    return set(zip(path[:-1], path[1:]))

shortest_path = routes["shortest_distance"]["path"]
lowest_cost_path = routes["lowest_cost"]["path"]

shortest_edges = path_to_edges(shortest_path)
cost_edges = path_to_edges(lowest_cost_path)

# 2. Classify
shared = shortest_edges & cost_edges
shortest_only = shortest_edges - cost_edges
cost_only = cost_edges - shortest_edges

print("Shared edges:", len(shared))
print("Shortest-only edges:", len(shortest_only))
print("Lowest-cost-only edges:", len(cost_only))

# 3. Get the edges table and select each group
edges_flat = ox.graph_to_gdfs(graph, nodes=False).reset_index()  # has u, v, key columns

def pick(edge_set):
    mask = [(u, v) in edge_set for u, v in zip(edges_flat["u"], edges_flat["v"])]
    return edges_flat[mask]

shared_gdf = pick(shared)
shortest_only_gdf = pick(shortest_only)
cost_only_gdf = pick(cost_only)

# 4. Draw faint background map
fig, ax = ox.plot_graph(
    graph,
    node_size=0,
    edge_color="#dddddd",
    edge_linewidth=0.4,
    bgcolor="white",
    show=False,
    close=False
)

# 5. Draw groups: shared first, differences on top
shared_gdf.plot(ax=ax, color="gray", linewidth=4)
shortest_only_gdf.plot(ax=ax, color="blue", linewidth=4)
cost_only_gdf.plot(ax=ax, color="red", linewidth=4)

# 6. Zoom to the two routes only
route_nodes = set(shortest_path) | set(lowest_cost_path)
xs = [graph.nodes[n]["x"] for n in route_nodes]
ys = [graph.nodes[n]["y"] for n in route_nodes]
pad_x = (max(xs) - min(xs)) * 0.1
pad_y = (max(ys) - min(ys)) * 0.1
ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)

# 7. Legend and title
ax.legend(
    handles=[
        Line2D([0], [0], color="gray", lw=4, label="Shared by both"),
        Line2D([0], [0], color="blue", lw=4, label="Shortest-distance only"),
        Line2D([0], [0], color="red", lw=4, label="Lowest-cost only"),
    ],
    loc="upper left"
)
ax.set_title("Plaça Catalunya → Sagrada Família: Shortest vs Lowest-Cost Route")

plt.savefig("route_comparison.png", dpi=300, bbox_inches="tight")
plt.show()

import matplotlib.pyplot as plt

# 1. Get the data from comparison_df (no hard-coded numbers)
plot_df = comparison_df.set_index("strategy").loc[["shortest_distance", "lowest_cost"]]

labels = ["Shortest-distance\nroute", "Lowest-cost route\n(slightly longer)"]
fuel  = plot_df["fuel_cost_eur"].values
wage  = plot_df["wage_cost_eur"].values
total = plot_df["total_cost_eur"].values

# 2. Calculate the numbers used in the text
fuel_change = fuel[1] - fuel[0]
wage_saving = wage[0] - wage[1]
net_saving  = total[0] - total[1]
net_pct     = net_saving / total[0] * 100

# 3. Create the chart
fig, ax = plt.subplots(figsize=(8, 6))

ax.bar(labels, fuel, width=0.5, color="#4C72B0", label="Fuel / distance cost")
ax.bar(labels, wage, width=0.5, bottom=fuel, color="#DD8452", label="Driver wage cost")

# 4. Labels inside the blocks and totals on top
for i in range(2):
    ax.text(i, fuel[i] / 2, f"€{fuel[i]:.2f}",
            ha="center", va="center", color="white", fontweight="bold")
    ax.text(i, fuel[i] + wage[i] / 2, f"€{wage[i]:.2f}",
            ha="center", va="center", color="white", fontweight="bold")
    ax.text(i, total[i] + 0.04, f"Total €{total[i]:.2f}",
            ha="center", va="bottom", fontsize=13, fontweight="bold")

# 5. Customize
ax.set_ylim(0, total.max() * 1.25)
ax.set_ylabel("Estimated operating cost (€)")
ax.set_title("Why the slightly longer route is cheaper",
             fontsize=15, fontweight="bold", pad=35)
ax.text(0.5, 1.04,
        f"Fuel cost +€{fuel_change:.3f}  |  Driver wage cost −€{wage_saving:.2f}  |  "
        f"Net saving €{net_saving:.2f} ({net_pct:.1f}%)",
        transform=ax.transAxes, ha="center", fontsize=10.5, color="#444444")
ax.legend(loc="upper right", frameon=False)
ax.spines[["top", "right"]].set_visible(False)

# 6. Save and close
plt.savefig("cost_breakdown.png", dpi=300, bbox_inches="tight")
plt.show()
plt.close()