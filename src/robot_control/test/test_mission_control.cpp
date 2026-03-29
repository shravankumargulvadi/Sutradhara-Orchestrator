#include "robot_control/sector_route_registry.hpp"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <string>

namespace
{

class MissionControlTest : public ::testing::Test
{
protected:
    void SetUp() override
    {
        temp_dir_ = std::filesystem::temp_directory_path() / "mission_control_test";
        std::filesystem::create_directories(temp_dir_);

        sectors_file_ = (temp_dir_ / "sectors.yaml").string();
        routes_file_ = (temp_dir_ / "routes.yaml").string();

        std::ofstream sectors_stream(sectors_file_);
        sectors_stream << "sectors:\n"
                          "  - sector_id: sector_test\n"
                          "    display_name: Test Sector\n"
                          "    default_patrol_route: patrol_test\n"
                          "    assets:\n"
                          "      - row_01\n";
        sectors_stream.close();

        std::ofstream routes_stream(routes_file_);
        routes_stream << "routes:\n"
                         "  - route_id: patrol_test\n"
                         "    description: Test patrol route\n"
                         "    route_type: patrol\n"
                         "    sector_id: sector_test\n"
                         "    robot_type: uav\n"
                         "    nominal_altitude_m: 12.0\n"
                         "    waypoints:\n"
                         "      - {x: 1.0, y: 2.0, z: 12.0}\n"
                         "      - {x: 3.0, y: 4.0, z: 12.0}\n";
        routes_stream.close();
    }

    std::filesystem::path temp_dir_;
    std::string sectors_file_;
    std::string routes_file_;
};

TEST_F(MissionControlTest, ResolvesSectorPatrolToConfiguredRoute)
{
    SectorRouteRegistry registry;
    registry.load(sectors_file_, routes_file_);

    const auto resolved_route = registry.resolve_patrol_route("sector_test");
    ASSERT_TRUE(resolved_route.has_value());
    EXPECT_EQ(resolved_route->route_id, "patrol_test");
    ASSERT_EQ(resolved_route->waypoints.size(), 2u);
    EXPECT_DOUBLE_EQ(resolved_route->waypoints[0].x, 1.0);
    EXPECT_DOUBLE_EQ(resolved_route->waypoints[0].y, 2.0);
    EXPECT_DOUBLE_EQ(resolved_route->waypoints[0].z, 12.0);
    EXPECT_DOUBLE_EQ(resolved_route->waypoints[1].x, 3.0);
    EXPECT_DOUBLE_EQ(resolved_route->waypoints[1].y, 4.0);
    EXPECT_DOUBLE_EQ(resolved_route->waypoints[1].z, 12.0);
}

TEST_F(MissionControlTest, ReturnsEmptyForUnknownSector)
{
    SectorRouteRegistry registry;
    registry.load(sectors_file_, routes_file_);

    const auto resolved_route = registry.resolve_patrol_route("missing_sector");
    EXPECT_FALSE(resolved_route.has_value());
}

}  // namespace
