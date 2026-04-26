#include "robot_control/mission_control_node.hpp"
#include "robot_control/sector_route_registry.hpp"

#include "ament_index_cpp/get_package_share_directory.hpp"
#include "geometry_msgs/msg/pose_array.hpp"
#include "robot_control_interfaces/msg/task_command.hpp"
#include "robot_control_interfaces/msg/task_spec.hpp"
#include "robot_control_interfaces/msg/task_target.hpp"

#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace
{

std::string resolve_default_config_path(const std::string &filename)
{
    const auto share_dir = ament_index_cpp::get_package_share_directory("inspection_sim");
    return (std::filesystem::path(share_dir) / "config" / filename).string();
}

class MissionControlNodeImpl
{
public:
    explicit MissionControlNodeImpl(MissionControlNode *node) : node_(node)
    {
        node_->declare_parameter<double>("flight_altitude_m", 8.0);
        node_->declare_parameter<std::string>("sectors_file", resolve_default_config_path("sectors.yaml"));
        node_->declare_parameter<std::string>("routes_file", resolve_default_config_path("routes.yaml"));

        flight_altitude_m_ = node_->get_parameter("flight_altitude_m").as_double();
        sectors_file_ = node_->get_parameter("sectors_file").as_string();
        routes_file_ = node_->get_parameter("routes_file").as_string();

        load_route_registry();

        task_command_sub_ =
            node_->create_subscription<robot_control_interfaces::msg::TaskCommand>(
                "/orchestrator/task_command",
                10,
                std::bind(&MissionControlNodeImpl::task_command_callback, this, std::placeholders::_1));
    }

private:
    using PoseArrayPublisher = rclcpp::Publisher<geometry_msgs::msg::PoseArray>::SharedPtr;

    MissionControlNode *node_;
    std::unordered_map<std::string, PoseArrayPublisher> trajectory_publishers_;
    rclcpp::Subscription<robot_control_interfaces::msg::TaskCommand>::SharedPtr task_command_sub_;
    double flight_altitude_m_;
    std::string sectors_file_;
    std::string routes_file_;
    SectorRouteRegistry route_registry_;

    static std::string normalize_robot_id(const std::string &robot_id)
    {
        if (robot_id.empty()) {
            return {};
        }

        if (robot_id.front() == '/') {
            return robot_id;
        }

        return "/" + robot_id;
    }

    PoseArrayPublisher get_or_create_publisher(const std::string &robot_ns)
    {
        auto it = trajectory_publishers_.find(robot_ns);
        if (it != trajectory_publishers_.end()) {
            return it->second;
        }

        const std::string topic = robot_ns + "/trajectory_upload";
        auto publisher = node_->create_publisher<geometry_msgs::msg::PoseArray>(topic, 10);
        trajectory_publishers_.emplace(robot_ns, publisher);
        RCLCPP_INFO(node_->get_logger(), "Created trajectory publisher for %s", topic.c_str());
        return publisher;
    }

    void load_route_registry()
    {
        try {
            route_registry_.load(sectors_file_, routes_file_);
            RCLCPP_INFO(
                node_->get_logger(),
                "Loaded sector and route config from %s and %s",
                sectors_file_.c_str(),
                routes_file_.c_str());
        } catch (const std::exception &ex) {
            RCLCPP_ERROR(
                node_->get_logger(),
                "Failed to load sector/route config: %s",
                ex.what());
        }
    }

    geometry_msgs::msg::PoseArray build_pose_array_from_points(
        const std::vector<robot_control_interfaces::msg::Point2D> &points,
        const std::string &frame,
        double altitude_m) const
    {
        geometry_msgs::msg::PoseArray trajectory;
        trajectory.header.stamp = node_->now();
        trajectory.header.frame_id = frame.empty() ? "map" : frame;

        for (const auto &point : points) {
            geometry_msgs::msg::Pose pose;
            pose.position.x = point.x;
            pose.position.y = point.y;
            pose.position.z = -altitude_m;
            pose.orientation.w = 1.0;
            trajectory.poses.push_back(pose);
        }

        return trajectory;
    }

    geometry_msgs::msg::PoseArray build_pose_array_from_route(
        const RouteDefinition &route,
        const std::string &frame) const
    {
        geometry_msgs::msg::PoseArray trajectory;
        trajectory.header.stamp = node_->now();
        trajectory.header.frame_id = frame.empty() ? "map" : frame;

        for (const auto &waypoint : route.waypoints) {
            geometry_msgs::msg::Pose pose;
            pose.position.x = waypoint.x;
            pose.position.y = waypoint.y;
            pose.position.z = -waypoint.z;
            pose.orientation.w = 1.0;
            trajectory.poses.push_back(pose);
        }

        return trajectory;
    }

    bool is_sector_patrol_request(const robot_control_interfaces::msg::TaskCommand &command) const
    {
        return command.task.task_type == robot_control_interfaces::msg::TaskSpec::PATROL &&
               command.task.target.kind == robot_control_interfaces::msg::TaskTarget::SECTOR_ID &&
               !command.task.target.sector_id.empty();
    }

    void task_command_callback(const robot_control_interfaces::msg::TaskCommand::SharedPtr msg)
    {
        const std::string robot_ns = normalize_robot_id(msg->robot_id);
        if (robot_ns.empty()) {
            RCLCPP_WARN(node_->get_logger(), "Received TaskCommand with empty robot_id");
            return;
        }

        if (msg->type != robot_control_interfaces::msg::TaskCommand::ASSIGN) {
            RCLCPP_INFO(
                node_->get_logger(),
                "Ignoring TaskCommand type %u for %s: not implemented yet",
                msg->type,
                robot_ns.c_str());
            return;
        }

        auto publisher = get_or_create_publisher(robot_ns);
        geometry_msgs::msg::PoseArray trajectory;
        bool resolved_sector_route = false;

        if (is_sector_patrol_request(*msg)) {
            const auto resolved_route = route_registry_.resolve_patrol_route(msg->task.target.sector_id);
            if (!resolved_route.has_value()) {
                RCLCPP_WARN(
                    node_->get_logger(),
                    "Ignoring TaskCommand %s for %s: no patrol route found for sector '%s'",
                    msg->command_id.c_str(),
                    robot_ns.c_str(),
                    msg->task.target.sector_id.c_str());
                return;
            }

            trajectory = build_pose_array_from_route(*resolved_route, msg->task.target.frame);
            resolved_sector_route = true;

            RCLCPP_INFO(
                node_->get_logger(),
                "Resolved sector '%s' to patrol route '%s' with %zu waypoint(s)",
                msg->task.target.sector_id.c_str(),
                resolved_route->route_id.c_str(),
                trajectory.poses.size());
        } else {
            const auto &target = msg->task.target;
            if (target.kind != robot_control_interfaces::msg::TaskTarget::POINT &&
                target.kind != robot_control_interfaces::msg::TaskTarget::REGION) {
                RCLCPP_WARN(
                    node_->get_logger(),
                    "Ignoring TaskCommand %s for %s: unsupported target kind %u",
                    msg->command_id.c_str(),
                    robot_ns.c_str(),
                    target.kind);
                return;
            }

            if (target.points.empty()) {
                RCLCPP_WARN(
                    node_->get_logger(),
                    "Ignoring TaskCommand %s for %s: target contains no points",
                    msg->command_id.c_str(),
                    robot_ns.c_str());
                return;
            }

            trajectory = build_pose_array_from_points(target.points, target.frame, flight_altitude_m_);
        }

        publisher->publish(trajectory);

        RCLCPP_INFO(
            node_->get_logger(),
            "Published %zu waypoint(s) for robot %s from task %s%s",
            trajectory.poses.size(),
            robot_ns.c_str(),
            msg->task_id.c_str(),
            resolved_sector_route ? " (resolved from sector patrol)" : "");
    }
};

}  // namespace

MissionControlNode::MissionControlNode(const rclcpp::NodeOptions &options)
    : rclcpp::Node("mission_control_node", options)
{
    static auto impls = std::vector<std::shared_ptr<MissionControlNodeImpl>>{};
    impls.push_back(std::make_shared<MissionControlNodeImpl>(this));
}
