#include "ament_index_cpp/get_package_share_directory.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "rclcpp/rclcpp.hpp"
#include "robot_control/sector_route_registry.hpp"
#include "robot_control_interfaces/msg/capability_profile.hpp"
#include "robot_control_interfaces/msg/robot_state.hpp"
#include "robot_control_interfaces/msg/task_ack.hpp"
#include "robot_control_interfaces/msg/task_command.hpp"
#include "robot_control_interfaces/msg/task_spec.hpp"
#include "robot_control_interfaces/msg/task_target.hpp"
#include "robot_control_interfaces/msg/task_update.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <iomanip>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

using namespace std::chrono_literals;

namespace
{

std::string resolve_default_config_path(const std::string &filename)
{
    const auto share_dir = ament_index_cpp::get_package_share_directory("inspection_sim");
    return (std::filesystem::path(share_dir) / "config" / filename).string();
}

std::string iso_timestamp_now()
{
    const auto now = std::chrono::system_clock::now();
    const auto time = std::chrono::system_clock::to_time_t(now);
    std::tm utc_time{};
#if defined(_WIN32)
    gmtime_s(&utc_time, &time);
#else
    gmtime_r(&time, &utc_time);
#endif
    std::ostringstream oss;
    oss << std::put_time(&utc_time, "%Y-%m-%dT%H:%M:%S+00:00");
    return oss.str();
}

double yaw_from_quaternion(
    const geometry_msgs::msg::Quaternion &q)
{
    const double siny_cosp = 2.0 * (q.w * q.z + q.x * q.y);
    const double cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z);
    return std::atan2(siny_cosp, cosy_cosp);
}

double normalize_angle(double angle)
{
    while (angle > M_PI) {
        angle -= 2.0 * M_PI;
    }
    while (angle < -M_PI) {
        angle += 2.0 * M_PI;
    }
    return angle;
}

struct GroundWaypoint
{
    double x{};
    double y{};
};

struct TaskContext
{
    std::string mission_id;
    std::string task_id;
    std::string command_id;
    uint8_t task_type{};
    uint8_t target_kind{};
    std::string sector_id;
    std::string asset_id;

    static TaskContext from_command(const robot_control_interfaces::msg::TaskCommand &command)
    {
        TaskContext context;
        context.mission_id = command.mission_id;
        context.task_id = command.task_id;
        context.command_id = command.command_id;
        context.task_type = command.task.task_type;
        context.target_kind = command.task.target.kind;
        context.sector_id = command.task.target.sector_id;
        context.asset_id = command.task.target.asset_id;
        return context;
    }
};

}  // namespace

class GroundRobotManager : public rclcpp::Node
{
public:
    GroundRobotManager() : Node("ground_robot_manager")
    {
        declare_parameter<std::string>("robot_id", "ugv_1");
        declare_parameter<std::string>("odom_topic", "/ugv_1/odom");
        declare_parameter<double>("max_speed_mps", 1.5);
        declare_parameter<double>("max_run_time_s", 3600.0);
        declare_parameter<double>("battery_pct", 100.0);
        declare_parameter<double>("goal_tolerance_m", 0.75);
        declare_parameter<double>("max_angular_speed_radps", 1.0);
        declare_parameter<std::string>("sectors_file", resolve_default_config_path("sectors.yaml"));
        declare_parameter<std::string>("routes_file", resolve_default_config_path("routes.yaml"));

        robot_id_ = get_parameter("robot_id").as_string();
        odom_topic_ = get_parameter("odom_topic").as_string();
        max_speed_mps_ = get_parameter("max_speed_mps").as_double();
        max_run_time_s_ = get_parameter("max_run_time_s").as_double();
        battery_pct_ = get_parameter("battery_pct").as_double();
        goal_tolerance_m_ = get_parameter("goal_tolerance_m").as_double();
        max_angular_speed_radps_ = get_parameter("max_angular_speed_radps").as_double();
        sectors_file_ = get_parameter("sectors_file").as_string();
        routes_file_ = get_parameter("routes_file").as_string();

        load_route_registry();

        capability_profile_pub_ =
            create_publisher<robot_control_interfaces::msg::CapabilityProfile>(
                "/orchestrator/capability_profile", 10);
        robot_state_pub_ =
            create_publisher<robot_control_interfaces::msg::RobotState>(
                "/orchestrator/robot_state", 10);
        cmd_vel_pub_ = create_publisher<geometry_msgs::msg::Twist>("/ugv_1/cmd_vel", 10);
        task_ack_pub_ = create_publisher<robot_control_interfaces::msg::TaskAck>(
            "/orchestrator/task_ack", 10);
        task_update_pub_ = create_publisher<robot_control_interfaces::msg::TaskUpdate>(
            "/orchestrator/task_update", 10);

        odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
            odom_topic_,
            10,
            std::bind(&GroundRobotManager::odom_callback, this, std::placeholders::_1));
        task_command_sub_ = create_subscription<robot_control_interfaces::msg::TaskCommand>(
            "/orchestrator/task_command",
            10,
            std::bind(&GroundRobotManager::task_command_callback, this, std::placeholders::_1));

        control_timer_ = create_wall_timer(100ms, std::bind(&GroundRobotManager::control_loop, this));
        robot_state_timer_ = create_wall_timer(1s, std::bind(&GroundRobotManager::publish_robot_state, this));
        capability_profile_timer_ =
            create_wall_timer(2s, std::bind(&GroundRobotManager::publish_capability_profile, this));

        publish_capability_profile();

        RCLCPP_INFO(
            get_logger(),
            "Ground robot manager ready for %s using odometry topic %s",
            robot_id_.c_str(),
            odom_topic_.c_str());
    }

private:
    std::string robot_id_;
    std::string odom_topic_;
    double max_speed_mps_{1.5};
    double max_run_time_s_{3600.0};
    double battery_pct_{100.0};
    double goal_tolerance_m_{0.75};
    double max_angular_speed_radps_{1.0};
    double x_m_{0.0};
    double y_m_{0.0};
    double yaw_rad_{0.0};
    double velocity_mps_{0.0};
    int32_t heartbeat_counter_{0};
    bool have_odom_{false};
    std::string sectors_file_;
    std::string routes_file_;
    SectorRouteRegistry route_registry_;
    std::optional<TaskContext> active_task_context_;
    std::vector<GroundWaypoint> waypoints_;
    std::size_t waypoint_index_{0};
    double initial_route_length_m_{0.0};
    float last_progress_pct_{-1.0f};

    rclcpp::Publisher<robot_control_interfaces::msg::CapabilityProfile>::SharedPtr capability_profile_pub_;
    rclcpp::Publisher<robot_control_interfaces::msg::RobotState>::SharedPtr robot_state_pub_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
    rclcpp::Publisher<robot_control_interfaces::msg::TaskAck>::SharedPtr task_ack_pub_;
    rclcpp::Publisher<robot_control_interfaces::msg::TaskUpdate>::SharedPtr task_update_pub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Subscription<robot_control_interfaces::msg::TaskCommand>::SharedPtr task_command_sub_;
    rclcpp::TimerBase::SharedPtr control_timer_;
    rclcpp::TimerBase::SharedPtr robot_state_timer_;
    rclcpp::TimerBase::SharedPtr capability_profile_timer_;

    void load_route_registry()
    {
        try {
            route_registry_.load(sectors_file_, routes_file_);
            RCLCPP_INFO(
                get_logger(),
                "Loaded ground route registry from %s and %s",
                sectors_file_.c_str(),
                routes_file_.c_str());
        } catch (const std::exception &ex) {
            RCLCPP_ERROR(get_logger(), "Failed to load ground route registry: %s", ex.what());
        }
    }

    void odom_callback(const nav_msgs::msg::Odometry::SharedPtr msg)
    {
        x_m_ = msg->pose.pose.position.x;
        y_m_ = msg->pose.pose.position.y;
        yaw_rad_ = yaw_from_quaternion(msg->pose.pose.orientation);

        const auto &linear = msg->twist.twist.linear;
        velocity_mps_ = std::sqrt(
            linear.x * linear.x +
            linear.y * linear.y +
            linear.z * linear.z);
        have_odom_ = true;
    }

    void publish_capability_profile()
    {
        robot_control_interfaces::msg::CapabilityProfile msg;
        msg.robot_id = robot_id_;
        msg.platform = robot_control_interfaces::msg::CapabilityProfile::PLATFORM_AMR;
        msg.max_speed_mps = static_cast<float>(max_speed_mps_);
        msg.max_run_time_s = static_cast<float>(max_run_time_s_);
        msg.sensors = {"RGB", "DEPTH", "LIDAR", "IMU"};
        msg.task_types_supported = {
            robot_control_interfaces::msg::CapabilityProfile::TASK_INSPECT,
            robot_control_interfaces::msg::CapabilityProfile::TASK_VERIFY,
            robot_control_interfaces::msg::CapabilityProfile::TASK_PATROL};
        capability_profile_pub_->publish(msg);
    }

    void publish_robot_state()
    {
        robot_control_interfaces::msg::RobotState msg;
        msg.robot_id = robot_id_;
        msg.mission_id = active_task_context_ ? active_task_context_->mission_id : "";
        msg.current_task_id = active_task_context_ ? active_task_context_->task_id : "";
        msg.x_m = static_cast<float>(x_m_);
        msg.y_m = static_cast<float>(y_m_);
        msg.yaw_rad = static_cast<float>(yaw_rad_);
        msg.z_m = 0.0f;
        msg.velocity_mps = static_cast<float>(velocity_mps_);
        msg.battery_pct = static_cast<float>(std::clamp(battery_pct_, 0.0, 100.0));
        msg.health_status = have_odom_
                                ? robot_control_interfaces::msg::RobotState::HEALTH_OK
                                : robot_control_interfaces::msg::RobotState::HEALTH_DEGRADED;
        msg.faults = have_odom_ ? std::vector<std::string>{} : std::vector<std::string>{"ODOM_NOT_RECEIVED"};
        msg.availability_status = !have_odom_
                                      ? robot_control_interfaces::msg::RobotState::AVAIL_OFFLINE
                                      : active_task_context_
                                          ? robot_control_interfaces::msg::RobotState::AVAIL_BUSY
                                          : robot_control_interfaces::msg::RobotState::AVAIL_IDLE;
        msg.heartbeat = heartbeat_counter_++;
        robot_state_pub_->publish(msg);
    }

    void task_command_callback(const robot_control_interfaces::msg::TaskCommand::SharedPtr msg)
    {
        if (msg->robot_id != robot_id_) {
            return;
        }

        const auto context = TaskContext::from_command(*msg);

        if (msg->type != robot_control_interfaces::msg::TaskCommand::ASSIGN) {
            publish_task_ack(
                context,
                robot_control_interfaces::msg::TaskAck::REJECTED,
                robot_control_interfaces::msg::TaskAck::REASON_INTERNAL_ERROR,
                "Only ASSIGN commands are implemented for ground robot manager.");
            return;
        }

        if (active_task_context_) {
            publish_task_ack(
                context,
                robot_control_interfaces::msg::TaskAck::REJECTED,
                robot_control_interfaces::msg::TaskAck::REASON_BUSY,
                "Ground robot is already executing another task.");
            return;
        }

        if (!have_odom_) {
            publish_task_ack(
                context,
                robot_control_interfaces::msg::TaskAck::REJECTED,
                robot_control_interfaces::msg::TaskAck::REASON_INTERNAL_ERROR,
                "Ground robot odometry is not available yet.");
            return;
        }

        if (battery_pct_ < msg->task.constraints.min_battery_pct_to_start) {
            publish_task_ack(
                context,
                robot_control_interfaces::msg::TaskAck::REJECTED,
                robot_control_interfaces::msg::TaskAck::REASON_LOW_BATTERY,
                "Ground robot battery is below the required start threshold.");
            return;
        }

        std::vector<GroundWaypoint> resolved_waypoints;
        std::string reject_detail;
        if (!resolve_waypoints(*msg, resolved_waypoints, reject_detail)) {
            publish_task_ack(
                context,
                robot_control_interfaces::msg::TaskAck::REJECTED,
                robot_control_interfaces::msg::TaskAck::REASON_TARGET_INVALID,
                reject_detail);
            return;
        }

        active_task_context_ = context;
        waypoints_ = resolved_waypoints;
        waypoint_index_ = 0;
        initial_route_length_m_ = std::max(remaining_route_distance(), 0.1);
        last_progress_pct_ = -1.0f;

        publish_task_ack(context, robot_control_interfaces::msg::TaskAck::ACCEPTED);
        publish_task_update(
            context,
            robot_control_interfaces::msg::TaskUpdate::STATUS_IN_PROGRESS,
            0.0f,
            "Ground route accepted; beginning waypoint patrol.");

        RCLCPP_INFO(
            get_logger(),
            "Accepted ground task %s with %zu waypoint(s)",
            context.task_id.c_str(),
            waypoints_.size());
    }

    bool resolve_waypoints(
        const robot_control_interfaces::msg::TaskCommand &command,
        std::vector<GroundWaypoint> &resolved_waypoints,
        std::string &reject_detail) const
    {
        const auto &target = command.task.target;
        if (command.task.task_type == robot_control_interfaces::msg::TaskSpec::PATROL &&
            target.kind == robot_control_interfaces::msg::TaskTarget::SECTOR_ID &&
            !target.sector_id.empty()) {
            const auto route = route_registry_.resolve_patrol_route(target.sector_id);
            if (!route.has_value()) {
                reject_detail = "No configured patrol route found for sector '" + target.sector_id + "'.";
                return false;
            }

            for (const auto &waypoint : route->waypoints) {
                resolved_waypoints.push_back({waypoint.x, waypoint.y});
            }
            return !resolved_waypoints.empty();
        }

        if (target.kind != robot_control_interfaces::msg::TaskTarget::POINT &&
            target.kind != robot_control_interfaces::msg::TaskTarget::REGION) {
            reject_detail = "Ground robot supports POINT, REGION, and sector PATROL targets only.";
            return false;
        }

        if (target.points.empty()) {
            reject_detail = "Ground target contains no points.";
            return false;
        }

        for (const auto &point : target.points) {
            resolved_waypoints.push_back({point.x, point.y});
        }
        return true;
    }

    void publish_task_ack(
        const TaskContext &context,
        uint8_t decision,
        uint8_t reject_reason_code = robot_control_interfaces::msg::TaskAck::REASON_NONE,
        const std::string &reject_reason_detail = "")
    {
        robot_control_interfaces::msg::TaskAck msg;
        msg.mission_id = context.mission_id;
        msg.robot_id = robot_id_;
        msg.task_id = context.task_id;
        msg.command_id = context.command_id;
        msg.decision = decision;
        msg.reject_reason_code = reject_reason_code;
        msg.reject_reason_detail = reject_reason_detail;
        task_ack_pub_->publish(msg);
    }

    void publish_task_update(
        const TaskContext &context,
        uint8_t status,
        float progress_pct,
        const std::string &detail)
    {
        robot_control_interfaces::msg::TaskUpdate msg;
        msg.mission_id = context.mission_id;
        msg.robot_id = robot_id_;
        msg.task_id = context.task_id;
        msg.status = status;
        msg.progress_pct = progress_pct;
        msg.status_detail = detail;
        msg.timestamp = iso_timestamp_now();
        task_update_pub_->publish(msg);
    }

    void control_loop()
    {
        if (!active_task_context_ || waypoint_index_ >= waypoints_.size()) {
            publish_stop();
            return;
        }

        if (!have_odom_) {
            return;
        }

        const auto &target = waypoints_[waypoint_index_];
        const double dx = target.x - x_m_;
        const double dy = target.y - y_m_;
        const double dist = std::sqrt(dx * dx + dy * dy);

        if (dist <= goal_tolerance_m_) {
            ++waypoint_index_;
            publish_progress();
            if (waypoint_index_ >= waypoints_.size()) {
                complete_active_task();
            }
            return;
        }

        const double desired_yaw = std::atan2(dy, dx);
        const double yaw_error = normalize_angle(desired_yaw - yaw_rad_);
        geometry_msgs::msg::Twist cmd;
        cmd.angular.z = std::clamp(1.8 * yaw_error, -max_angular_speed_radps_, max_angular_speed_radps_);
        const double heading_scale = std::max(0.0, 1.0 - std::min(std::abs(yaw_error), M_PI) / M_PI);
        cmd.linear.x = std::clamp(0.7 * dist * heading_scale, 0.0, max_speed_mps_);
        cmd_vel_pub_->publish(cmd);
    }

    void publish_progress()
    {
        if (!active_task_context_) {
            return;
        }

        const auto remaining = remaining_route_distance();
        const float progress_pct = static_cast<float>(
            std::clamp(100.0 * (1.0 - remaining / initial_route_length_m_), 0.0, 99.0));
        if (progress_pct <= last_progress_pct_) {
            return;
        }

        last_progress_pct_ = progress_pct;
        std::ostringstream detail;
        detail << "Reached ground waypoint " << waypoint_index_ << " of " << waypoints_.size() << ".";
        publish_task_update(
            *active_task_context_,
            robot_control_interfaces::msg::TaskUpdate::STATUS_IN_PROGRESS,
            progress_pct,
            detail.str());
    }

    double remaining_route_distance() const
    {
        if (waypoint_index_ >= waypoints_.size()) {
            return 0.0;
        }

        double remaining = 0.0;
        double prev_x = x_m_;
        double prev_y = y_m_;
        for (std::size_t i = waypoint_index_; i < waypoints_.size(); ++i) {
            const double dx = waypoints_[i].x - prev_x;
            const double dy = waypoints_[i].y - prev_y;
            remaining += std::sqrt(dx * dx + dy * dy);
            prev_x = waypoints_[i].x;
            prev_y = waypoints_[i].y;
        }
        return remaining;
    }

    void complete_active_task()
    {
        if (active_task_context_) {
            publish_task_update(
                *active_task_context_,
                robot_control_interfaces::msg::TaskUpdate::STATUS_COMPLETED,
                100.0f,
                "Ground patrol route completed.");
        }

        publish_stop();
        active_task_context_.reset();
        waypoints_.clear();
        waypoint_index_ = 0;
        initial_route_length_m_ = 0.0;
        last_progress_pct_ = -1.0f;
    }

    void publish_stop()
    {
        geometry_msgs::msg::Twist cmd;
        cmd_vel_pub_->publish(cmd);
    }
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<GroundRobotManager>());
    rclcpp::shutdown();
    return 0;
}
