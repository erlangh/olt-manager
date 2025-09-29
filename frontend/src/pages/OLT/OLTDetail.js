import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Descriptions,
  Tag,
  Button,
  Space,
  Table,
  Progress,
  Statistic,
  Tabs,
  Alert,
  Badge,
  Tooltip,
  Modal,
  Form,
  Input,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  RouterOutlined,
  WifiOutlined,
  SettingOutlined,
  MonitorOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';

const { TabPane } = Tabs;

const OLTDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [olt, setOlt] = useState(null);
  const [ports, setPorts] = useState([]);
  const [onts, setOnts] = useState([]);
  const [alarms, setAlarms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [form] = Form.useForm();

  // Sample data
  const sampleOlt = {
    id: parseInt(id),
    name: 'OLT-Central-01',
    ip_address: '192.168.1.100',
    model: 'ZTE C320',
    location: 'Central Office',
    status: 'online',
    total_ports: 16,
    active_ports: 12,
    total_onts: 245,
    active_onts: 238,
    uptime: '15 days 8 hours',
    firmware_version: '2.1.5',
    snmp_community: 'public',
    snmp_port: 161,
    snmp_version: '2c',
    cpu_usage: 45,
    memory_usage: 62,
    temperature: 38,
    power_consumption: 85,
    created_at: '2024-01-15T10:30:00Z',
    last_seen: '2024-03-15T14:25:00Z',
  };

  const samplePorts = [
    { id: 1, port_number: '1/1/1', status: 'up', ont_count: 16, max_onts: 128, utilization: 12.5 },
    { id: 2, port_number: '1/1/2', status: 'up', ont_count: 24, max_onts: 128, utilization: 18.75 },
    { id: 3, port_number: '1/1/3', status: 'down', ont_count: 0, max_onts: 128, utilization: 0 },
    { id: 4, port_number: '1/1/4', status: 'up', ont_count: 32, max_onts: 128, utilization: 25 },
  ];

  const sampleOnts = [
    { id: 1, serial_number: 'ZTEG12345678', port: '1/1/1', status: 'online', signal_level: -18.5, distance: 1.2 },
    { id: 2, serial_number: 'ZTEG12345679', port: '1/1/1', status: 'online', signal_level: -20.1, distance: 2.1 },
    { id: 3, serial_number: 'ZTEG12345680', port: '1/1/2', status: 'offline', signal_level: null, distance: null },
  ];

  const sampleAlarms = [
    { id: 1, severity: 'critical', message: 'Port 1/1/3 is down', timestamp: '2024-03-15T14:20:00Z' },
    { id: 2, severity: 'warning', message: 'High temperature detected', timestamp: '2024-03-15T13:45:00Z' },
    { id: 3, severity: 'info', message: 'ONT ZTEG12345680 disconnected', timestamp: '2024-03-15T12:30:00Z' },
  ];

  useEffect(() => {
    fetchOltDetail();
  }, [id]);

  const fetchOltDetail = async () => {
    setLoading(true);
    try {
      // Simulate API calls
      setTimeout(() => {
        setOlt(sampleOlt);
        setPorts(samplePorts);
        setOnts(sampleOnts);
        setAlarms(sampleAlarms);
        setLoading(false);
      }, 1000);
    } catch (error) {
      message.error('Gagal memuat detail OLT');
      setLoading(false);
    }
  };

  const handleEdit = () => {
    form.setFieldsValue(olt);
    setEditModalVisible(true);
  };

  const handleUpdate = async (values) => {
    try {
      setOlt({ ...olt, ...values });
      setEditModalVisible(false);
      message.success('OLT berhasil diperbarui');
    } catch (error) {
      message.error('Gagal memperbarui OLT');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online':
      case 'up':
        return 'success';
      case 'offline':
      case 'down':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getAlarmColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'processing';
      default:
        return 'default';
    }
  };

  const portColumns = [
    {
      title: 'Port',
      dataIndex: 'port_number',
      key: 'port_number',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'ONT Count',
      key: 'ont_count',
      render: (_, record) => (
        <span>{record.ont_count}/{record.max_onts}</span>
      ),
    },
    {
      title: 'Utilization',
      dataIndex: 'utilization',
      key: 'utilization',
      render: (utilization) => (
        <Progress
          percent={utilization}
          size="small"
          status={utilization > 80 ? 'exception' : utilization > 60 ? 'active' : 'success'}
        />
      ),
    },
  ];

  const ontColumns = [
    {
      title: 'Serial Number',
      dataIndex: 'serial_number',
      key: 'serial_number',
    },
    {
      title: 'Port',
      dataIndex: 'port',
      key: 'port',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Signal Level (dBm)',
      dataIndex: 'signal_level',
      key: 'signal_level',
      render: (level) => level ? level.toFixed(1) : 'N/A',
    },
    {
      title: 'Distance (km)',
      dataIndex: 'distance',
      key: 'distance',
      render: (distance) => distance ? distance.toFixed(1) : 'N/A',
    },
  ];

  const alarmColumns = [
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity) => (
        <Badge color={getAlarmColor(severity)} text={severity.toUpperCase()} />
      ),
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
    },
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp) => new Date(timestamp).toLocaleString(),
    },
  ];

  if (!olt) {
    return <div>Loading...</div>;
  }

  return (
    <div className="olt-detail-page">
      <Card
        title={
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/olts')}
            >
              Kembali
            </Button>
            <RouterOutlined />
            <span>{olt.name}</span>
            <Tag color={getStatusColor(olt.status)}>
              {olt.status.toUpperCase()}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchOltDetail}
              loading={loading}
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={handleEdit}
            >
              Edit
            </Button>
          </Space>
        }
      >
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="CPU Usage"
                value={olt.cpu_usage}
                suffix="%"
                valueStyle={{
                  color: olt.cpu_usage > 80 ? '#cf1322' : olt.cpu_usage > 60 ? '#d48806' : '#3f8600'
                }}
              />
              <Progress
                percent={olt.cpu_usage}
                showInfo={false}
                status={olt.cpu_usage > 80 ? 'exception' : 'success'}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Memory Usage"
                value={olt.memory_usage}
                suffix="%"
                valueStyle={{
                  color: olt.memory_usage > 80 ? '#cf1322' : olt.memory_usage > 60 ? '#d48806' : '#3f8600'
                }}
              />
              <Progress
                percent={olt.memory_usage}
                showInfo={false}
                status={olt.memory_usage > 80 ? 'exception' : 'success'}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Temperature"
                value={olt.temperature}
                suffix="°C"
                valueStyle={{
                  color: olt.temperature > 50 ? '#cf1322' : olt.temperature > 40 ? '#d48806' : '#3f8600'
                }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Power"
                value={olt.power_consumption}
                suffix="W"
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
        </Row>

        <Tabs defaultActiveKey="overview">
          <TabPane tab="Overview" key="overview">
            <Row gutter={16}>
              <Col span={12}>
                <Card title="Informasi Dasar" size="small">
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="Nama">{olt.name}</Descriptions.Item>
                    <Descriptions.Item label="IP Address">{olt.ip_address}</Descriptions.Item>
                    <Descriptions.Item label="Model">{olt.model}</Descriptions.Item>
                    <Descriptions.Item label="Lokasi">{olt.location}</Descriptions.Item>
                    <Descriptions.Item label="Firmware">{olt.firmware_version}</Descriptions.Item>
                    <Descriptions.Item label="Uptime">{olt.uptime}</Descriptions.Item>
                  </Descriptions>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="Konfigurasi SNMP" size="small">
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="Community">{olt.snmp_community}</Descriptions.Item>
                    <Descriptions.Item label="Port">{olt.snmp_port}</Descriptions.Item>
                    <Descriptions.Item label="Version">{olt.snmp_version}</Descriptions.Item>
                    <Descriptions.Item label="Created">{new Date(olt.created_at).toLocaleString()}</Descriptions.Item>
                    <Descriptions.Item label="Last Seen">{new Date(olt.last_seen).toLocaleString()}</Descriptions.Item>
                  </Descriptions>
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab={`Ports (${ports.length})`} key="ports">
            <Table
              columns={portColumns}
              dataSource={ports}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </TabPane>

          <TabPane tab={`ONTs (${onts.length})`} key="onts">
            <Table
              columns={ontColumns}
              dataSource={onts}
              rowKey="id"
              size="small"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
              }}
            />
          </TabPane>

          <TabPane tab={`Alarms (${alarms.length})`} key="alarms">
            <Table
              columns={alarmColumns}
              dataSource={alarms}
              rowKey="id"
              size="small"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title="Edit OLT"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleUpdate}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Nama OLT"
                rules={[{ required: true, message: 'Nama OLT wajib diisi' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="ip_address"
                label="IP Address"
                rules={[{ required: true, message: 'IP Address wajib diisi' }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="location"
                label="Lokasi"
                rules={[{ required: true, message: 'Lokasi wajib diisi' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="snmp_community"
                label="SNMP Community"
                rules={[{ required: true, message: 'SNMP Community wajib diisi' }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Update
              </Button>
              <Button onClick={() => setEditModalVisible(false)}>
                Batal
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default OLTDetail;