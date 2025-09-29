import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Tooltip,
  Row,
  Col,
  Statistic,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  SearchOutlined,
  RouterOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Option } = Select;

const OLTList = () => {
  const [olts, setOlts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingOlt, setEditingOlt] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [form] = Form.useForm();
  const navigate = useNavigate();

  // Sample data - replace with actual API calls
  const sampleOlts = [
    {
      id: 1,
      name: 'OLT-Central-01',
      ip_address: '192.168.1.100',
      model: 'ZTE C320',
      location: 'Central Office',
      status: 'online',
      total_ports: 16,
      active_ports: 12,
      total_onts: 245,
      active_onts: 238,
      uptime: '15 days',
      firmware_version: '2.1.5',
      snmp_community: 'public',
      created_at: '2024-01-15',
    },
    {
      id: 2,
      name: 'OLT-Branch-02',
      ip_address: '192.168.1.101',
      model: 'ZTE C320',
      location: 'Branch Office A',
      status: 'offline',
      total_ports: 8,
      active_ports: 6,
      total_onts: 120,
      active_onts: 115,
      uptime: '0 days',
      firmware_version: '2.1.3',
      snmp_community: 'public',
      created_at: '2024-01-20',
    },
    {
      id: 3,
      name: 'OLT-Remote-03',
      ip_address: '192.168.1.102',
      model: 'ZTE C320',
      location: 'Remote Site B',
      status: 'warning',
      total_ports: 16,
      active_ports: 14,
      total_onts: 180,
      active_onts: 175,
      uptime: '8 days',
      firmware_version: '2.1.5',
      snmp_community: 'public',
      created_at: '2024-02-01',
    },
  ];

  useEffect(() => {
    fetchOlts();
  }, []);

  const fetchOlts = async () => {
    setLoading(true);
    try {
      // Simulate API call
      setTimeout(() => {
        setOlts(sampleOlts);
        setLoading(false);
      }, 1000);
    } catch (error) {
      message.error('Gagal memuat data OLT');
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingOlt(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingOlt(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      // Simulate API call
      setOlts(olts.filter(olt => olt.id !== id));
      message.success('OLT berhasil dihapus');
    } catch (error) {
      message.error('Gagal menghapus OLT');
    }
  };

  const handleSubmit = async (values) => {
    try {
      if (editingOlt) {
        // Update existing OLT
        const updatedOlts = olts.map(olt =>
          olt.id === editingOlt.id ? { ...olt, ...values } : olt
        );
        setOlts(updatedOlts);
        message.success('OLT berhasil diperbarui');
      } else {
        // Add new OLT
        const newOlt = {
          id: Date.now(),
          ...values,
          status: 'offline',
          total_ports: 16,
          active_ports: 0,
          total_onts: 0,
          active_onts: 0,
          uptime: '0 days',
          created_at: new Date().toISOString().split('T')[0],
        };
        setOlts([...olts, newOlt]);
        message.success('OLT berhasil ditambahkan');
      }
      setModalVisible(false);
      form.resetFields();
    } catch (error) {
      message.error('Gagal menyimpan data OLT');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online':
        return 'success';
      case 'offline':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online':
        return <CheckCircleOutlined />;
      case 'offline':
        return <CloseCircleOutlined />;
      case 'warning':
        return <ExclamationCircleOutlined />;
      default:
        return null;
    }
  };

  const columns = [
    {
      title: 'Nama OLT',
      dataIndex: 'name',
      key: 'name',
      filteredValue: searchText ? [searchText] : null,
      onFilter: (value, record) =>
        record.name.toLowerCase().includes(value.toLowerCase()) ||
        record.ip_address.includes(value) ||
        record.location.toLowerCase().includes(value.toLowerCase()),
      render: (text, record) => (
        <Space>
          <RouterOutlined />
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: 'Model',
      dataIndex: 'model',
      key: 'model',
    },
    {
      title: 'Lokasi',
      dataIndex: 'location',
      key: 'location',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Ports',
      key: 'ports',
      render: (_, record) => (
        <span>{record.active_ports}/{record.total_ports}</span>
      ),
    },
    {
      title: 'ONTs',
      key: 'onts',
      render: (_, record) => (
        <span>{record.active_onts}/{record.total_onts}</span>
      ),
    },
    {
      title: 'Uptime',
      dataIndex: 'uptime',
      key: 'uptime',
    },
    {
      title: 'Aksi',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="Lihat Detail">
            <Button
              type="primary"
              icon={<EyeOutlined />}
              size="small"
              onClick={() => navigate(`/olts/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              icon={<EditOutlined />}
              size="small"
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Hapus">
            <Popconfirm
              title="Apakah Anda yakin ingin menghapus OLT ini?"
              onConfirm={() => handleDelete(record.id)}
              okText="Ya"
              cancelText="Tidak"
            >
              <Button
                danger
                icon={<DeleteOutlined />}
                size="small"
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Calculate statistics
  const totalOlts = olts.length;
  const onlineOlts = olts.filter(olt => olt.status === 'online').length;
  const offlineOlts = olts.filter(olt => olt.status === 'offline').length;
  const warningOlts = olts.filter(olt => olt.status === 'warning').length;

  return (
    <div className="olt-list-page">
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total OLT"
              value={totalOlts}
              prefix={<RouterOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Online"
              value={onlineOlts}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Offline"
              value={offlineOlts}
              valueStyle={{ color: '#cf1322' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Warning"
              value={warningOlts}
              valueStyle={{ color: '#d48806' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="Daftar OLT"
        extra={
          <Space>
            <Input
              placeholder="Cari OLT..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 200 }}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchOlts}
              loading={loading}
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              Tambah OLT
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={olts}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} dari ${total} OLT`,
          }}
        />
      </Card>

      <Modal
        title={editingOlt ? 'Edit OLT' : 'Tambah OLT Baru'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Nama OLT"
                rules={[{ required: true, message: 'Nama OLT wajib diisi' }]}
              >
                <Input placeholder="Masukkan nama OLT" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="ip_address"
                label="IP Address"
                rules={[
                  { required: true, message: 'IP Address wajib diisi' },
                  { pattern: /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/, message: 'Format IP tidak valid' }
                ]}
              >
                <Input placeholder="192.168.1.100" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="model"
                label="Model"
                rules={[{ required: true, message: 'Model wajib diisi' }]}
              >
                <Select placeholder="Pilih model OLT">
                  <Option value="ZTE C320">ZTE C320</Option>
                  <Option value="ZTE C300">ZTE C300</Option>
                  <Option value="Huawei MA5800">Huawei MA5800</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="location"
                label="Lokasi"
                rules={[{ required: true, message: 'Lokasi wajib diisi' }]}
              >
                <Input placeholder="Masukkan lokasi OLT" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="snmp_community"
                label="SNMP Community"
                rules={[{ required: true, message: 'SNMP Community wajib diisi' }]}
              >
                <Input placeholder="public" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="firmware_version"
                label="Firmware Version"
              >
                <Input placeholder="2.1.5" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingOlt ? 'Update' : 'Tambah'}
              </Button>
              <Button onClick={() => setModalVisible(false)}>
                Batal
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default OLTList;