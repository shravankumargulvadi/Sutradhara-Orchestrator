#pragma once

#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

struct RouteWaypoint
{
    double x{};
    double y{};
    double z{};
};

struct RouteDefinition
{
    std::string route_id;
    std::string sector_id;
    std::string route_type;
    double nominal_altitude_m{};
    std::vector<RouteWaypoint> waypoints;
};

class SectorRouteRegistry
{
public:
    void load(const std::string &sectors_file, const std::string &routes_file);
    std::optional<RouteDefinition> resolve_patrol_route(const std::string &sector_id) const;

private:
    std::unordered_map<std::string, std::string> sector_default_routes_;
    std::unordered_map<std::string, RouteDefinition> routes_;
};
