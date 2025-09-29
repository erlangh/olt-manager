import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Progress, Table, Alert, Spin, Button } from 'antd';
import {
  RouterOutlined,
  WifiOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { useQuery } from 'react-query';
import { apiService } from '../services/api';
import { useWebSocket } from '../contexts/WebSocketContext';

const Dashboard = () => {
  const [refreshing, setRefreshing] = useState(false);
  const { subscribe } = useWebSocket();

  // Fetch dashboard data
  const { data: dashboardData, isLoading, error, refetch } = useQuery(
    'dashboard',
    apiService.monitoring.dashboard,
    {
      refetchInterval: 30000, // Refresh every 30 seconds
      refetchOnWindowFocus: true,
    }
  );

  // Subscribe to real-time updates
  useEffect(() => {
    const unsubscribe = subscribe('dashboard_update', (data) => {
      // Refetch dashboard data when updates are received
      refetch();
    });

    return unsubscribe;
  }, [subscribe, refetch]);

  // Handle manual refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  // Sample data for charts (will be replaced with real data)
  const performanceData = [
    { time: '00:00', cpu: 45, memory: 62, bandwidth: 78 },
    { time: '04:00', cpu: 52, memory: 58, bandwidth: 82 },
    { time: '08:00', cpu: 68, memory: 71, bandwidth: 91 },
    { time: '12:00', cpu: 75, memory: 69, bandwidth: 95 },
    { time: '16:00', cpu: 71, memory: 73, bandwidth: 88 },
    { time: '20:00', cpu: 58, memory: 65, bandwidth: 85 },
  ];

  const ontStatusData = [
    { name: 'Online', value: 245, color: '#52c41a' },
    { name: 'Offline', value: 23, color: '#ff4d4f' },
    { name: 'Pending', value: 12, color: '#faad14' },
  ];

  // Recent alarms columns
  const alarmColumns = [
    {
      title: 'Time',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (text) => new Date(text).toLocaleString(),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity) => (
        <span className={`alarm-severity alarm-${severity?.toLowerCase()}`}>
          {severity}
        </span>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
    },
  ];

  // Sample alarm data
  const recentAlarms = [
    {
      key: '1',
      timestamp: new Date().toISOString(),
      type: 'ONT Offline',
      severity: 'Warning',
      description: 'ONT 1/1/1 went offline',
    },
    {
      key: '2',
      timestamp: new Date(Date.now() - 300000).toISOString(),
      type: 'High Temperature',
      severity: 'Critical',
      description: 'OLT temperature exceeded threshold',
    },
  ];

  if (isLoading) {
    return (
      <div className="loading-container">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Error Loading Dashboard"
        description="Failed to load dashboard data. Please try again."
        type="error"
        showIcon
        action={
          <Button size="small" danger onClick={handleRefresh}>
            Retry
          </Button>
        }
      />
    );
  }

  const stats = dashboardData?.data || {};

  return (
    <div className="dashboard">
      <div className="page-header">
        <div className="page-title">
          <h1>Dashboard</h1>
          <p>OLT Management System Overview</p>
        </div>
        <div className="page-actions">
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={refreshing}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} className="stats-row">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total OLTs"
              value={stats.total_olts || 8}
              prefix={<RouterOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total ONTs"
              value={stats.total_onts || 280}
              prefix={<WifiOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Online ONTs"
              value={stats.online_onts || 245}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
            <Progress
              percent={Math.round(((stats.online_onts || 245) / (stats.total_onts || 280)) * 100)}
              size="small"
              showInfo={false}
              strokeColor="#52c41a"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Alarms"
              value={stats.active_alarms || 5}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]} className="charts-row">
        <Col xs={24} lg={16}>
          <Card title="System Performance (24h)" className="chart-card">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="cpu"
                  stroke="#1890ff"
                  name="CPU %"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="memory"
                  stroke="#52c41a"
                  name="Memory %"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="bandwidth"
                  stroke="#faad14"
                  name="Bandwidth %"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="ONT Status Distribution" className="chart-card">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={ontStatusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {ontStatusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="pie-legend">
              {ontStatusData.map((item, index) => (
                <div key={index} className="legend-item">
                  <span
                    className="legend-color"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="legend-text">
                    {item.name}: {item.value}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      {/* Recent Activity Row */}
      <Row gutter={[16, 16]} className="activity-row">
        <Col xs={24} lg={12}>
          <Card title="Recent Alarms" className="table-card">
            <Table
              columns={alarmColumns}
              dataSource={recentAlarms}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="System Health" className="health-card">
            <div className="health-metrics">
              <div className="health-item">
                <div className="health-label">OLT Connectivity</div>
                <Progress percent={95} status="active" strokeColor="#52c41a" />
              </div>
              <div className="health-item">
                <div className="health-label">Database Status</div>
                <Progress percent={100} strokeColor="#52c41a" />
              </div>
              <div className="health-item">
                <div className="health-label">SNMP Response</div>
                <Progress percent={88} strokeColor="#faad14" />
              </div>
              <div className="health-item">
                <div className="health-label">System Load</div>
                <Progress percent={65} strokeColor="#1890ff" />
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Network Overview */}
      <Row gutter={[16, 16]} className="network-row">
        <Col span={24}>
          <Card title="Network Traffic Overview" className="chart-card">
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="bandwidth"
                  stroke="#1890ff"
                  fill="#1890ff"
                  fillOpacity={0.3}
                  name="Bandwidth Utilization %"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;