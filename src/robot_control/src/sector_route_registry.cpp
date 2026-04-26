#include "robot_control/sector_route_registry.hpp"

#include "yaml-cpp/yaml.h"

#include <stdexcept>

void SectorRouteRegistry::load(const std::string &sectors_file, const std::string &routes_file)
{
    sector_default_routes_.clear();
    routes_.clear();

    const auto sectors_yaml = YAML::LoadFile(sectors_file);
    const auto routes_yaml = YAML::LoadFile(routes_file);

    const auto sectors_node = sectors_yaml["sectors"];
    if (!sectors_node || !sectors_node.IsSequence()) {
        throw std::runtime_error("Missing or invalid 'sectors' sequence");
    }

    for (const auto &sector_node : sectors_node) {
        const auto sector_id = sector_node["sector_id"].as<std::string>();
        const auto default_patrol_route = sector_node["default_patrol_route"].as<std::string>();
        sector_default_routes_[sector_id] = default_patrol_route;
    }

    const auto routes_node = routes_yaml["routes"];
    if (!routes_node || !routes_node.IsSequence()) {
        throw std::runtime_error("Missing or invalid 'routes' sequence");
    }

    for (const auto &route_node : routes_node) {
        RouteDefinition route;
        route.route_id = route_node["route_id"].as<std::string>();
        route.sector_id = route_node["sector_id"] ? route_node["sector_id"].as<std::string>() : "";
        route.route_type = route_node["route_type"] ? route_node["route_type"].as<std::string>() : "";
        route.nominal_altitude_m =
            route_node["nominal_altitude_m"] ? route_node["nominal_altitude_m"].as<double>() : 8.0;

        const auto waypoints_node = route_node["waypoints"];
        if (!waypoints_node || !waypoints_node.IsSequence()) {
            throw std::runtime_error("Route '" + route.route_id + "' is missing waypoints");
        }

        for (const auto &waypoint_node : waypoints_node) {
            RouteWaypoint waypoint;
            waypoint.x = waypoint_node["x"].as<double>();
            waypoint.y = waypoint_node["y"].as<double>();
            waypoint.z = waypoint_node["z"] ? waypoint_node["z"].as<double>() : route.nominal_altitude_m;
            route.waypoints.push_back(waypoint);
        }

        routes_[route.route_id] = route;
    }
}

std::optional<RouteDefinition> SectorRouteRegistry::resolve_patrol_route(const std::string &sector_id) const
{
    const auto sector_it = sector_default_routes_.find(sector_id);
    if (sector_it == sector_default_routes_.end()) {
        return std::nullopt;
    }

    const auto route_it = routes_.find(sector_it->second);
    if (route_it == routes_.end()) {
        return std::nullopt;
    }

    return route_it->second;
}
