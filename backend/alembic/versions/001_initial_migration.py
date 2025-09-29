"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('permissions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create olts table
    op.create_table('olts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('snmp_community', sa.String(length=100), nullable=False),
        sa.Column('snmp_version', sa.String(length=10), nullable=False),
        sa.Column('snmp_port', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        sa.Column('max_ports', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_olts_id'), 'olts', ['id'], unique=False)
    op.create_index(op.f('ix_olts_ip_address'), 'olts', ['ip_address'], unique=True)
    op.create_index(op.f('ix_olts_name'), 'olts', ['name'], unique=True)

    # Create service_profiles table
    op.create_table('service_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('downstream_bandwidth', sa.Integer(), nullable=False),
        sa.Column('upstream_bandwidth', sa.Integer(), nullable=False),
        sa.Column('vlan_id', sa.Integer(), nullable=True),
        sa.Column('service_type', sa.String(length=50), nullable=True),
        sa.Column('qos_profile', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_service_profiles_id'), 'service_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_service_profiles_name'), 'service_profiles', ['name'], unique=True)

    # Create olt_ports table
    op.create_table('olt_ports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('olt_id', sa.Integer(), nullable=False),
        sa.Column('port_number', sa.Integer(), nullable=False),
        sa.Column('port_type', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('admin_status', sa.String(length=20), nullable=True),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('max_onts', sa.Integer(), nullable=True),
        sa.Column('active_onts', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['olt_id'], ['olts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_olt_ports_id'), 'olt_ports', ['id'], unique=False)

    # Create onts table
    op.create_table('onts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('olt_id', sa.Integer(), nullable=False),
        sa.Column('port_id', sa.Integer(), nullable=False),
        sa.Column('ont_id', sa.Integer(), nullable=False),
        sa.Column('serial_number', sa.String(length=50), nullable=True),
        sa.Column('mac_address', sa.String(length=17), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('admin_status', sa.String(length=20), nullable=True),
        sa.Column('signal_level', sa.Float(), nullable=True),
        sa.Column('distance', sa.Float(), nullable=True),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('customer_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['olt_id'], ['olts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['port_id'], ['olt_ports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onts_id'), 'onts', ['id'], unique=False)
    op.create_index(op.f('ix_onts_serial_number'), 'onts', ['serial_number'], unique=False)

    # Create ont_services table
    op.create_table('ont_services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ont_id', sa.Integer(), nullable=False),
        sa.Column('service_profile_id', sa.Integer(), nullable=False),
        sa.Column('service_port', sa.Integer(), nullable=True),
        sa.Column('vlan_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ont_id'], ['onts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_profile_id'], ['service_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ont_services_id'), 'ont_services', ['id'], unique=False)

    # Create alarms table
    op.create_table('alarms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('olt_id', sa.Integer(), nullable=True),
        sa.Column('ont_id', sa.Integer(), nullable=True),
        sa.Column('port_id', sa.Integer(), nullable=True),
        sa.Column('alarm_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=True),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['olt_id'], ['olts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ont_id'], ['onts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['port_id'], ['olt_ports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alarms_id'), 'alarms', ['id'], unique=False)

    # Create performance_data table
    op.create_table('performance_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('olt_id', sa.Integer(), nullable=True),
        sa.Column('ont_id', sa.Integer(), nullable=True),
        sa.Column('port_id', sa.Integer(), nullable=True),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['olt_id'], ['olts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ont_id'], ['onts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['port_id'], ['olt_ports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_performance_data_id'), 'performance_data', ['id'], unique=False)
    op.create_index(op.f('ix_performance_data_timestamp'), 'performance_data', ['timestamp'], unique=False)

    # Create configurations table
    op.create_table('configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('olt_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config_type', sa.String(length=50), nullable=False),
        sa.Column('config_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['olt_id'], ['olts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_configurations_id'), 'configurations', ['id'], unique=False)

    # Create backups table
    op.create_table('backups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('olt_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('backup_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['olt_id'], ['olts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backups_id'), 'backups', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_backups_id'), table_name='backups')
    op.drop_table('backups')
    
    op.drop_index(op.f('ix_configurations_id'), table_name='configurations')
    op.drop_table('configurations')
    
    op.drop_index(op.f('ix_performance_data_timestamp'), table_name='performance_data')
    op.drop_index(op.f('ix_performance_data_id'), table_name='performance_data')
    op.drop_table('performance_data')
    
    op.drop_index(op.f('ix_alarms_id'), table_name='alarms')
    op.drop_table('alarms')
    
    op.drop_index(op.f('ix_ont_services_id'), table_name='ont_services')
    op.drop_table('ont_services')
    
    op.drop_index(op.f('ix_onts_serial_number'), table_name='onts')
    op.drop_index(op.f('ix_onts_id'), table_name='onts')
    op.drop_table('onts')
    
    op.drop_index(op.f('ix_olt_ports_id'), table_name='olt_ports')
    op.drop_table('olt_ports')
    
    op.drop_index(op.f('ix_service_profiles_name'), table_name='service_profiles')
    op.drop_index(op.f('ix_service_profiles_id'), table_name='service_profiles')
    op.drop_table('service_profiles')
    
    op.drop_index(op.f('ix_olts_name'), table_name='olts')
    op.drop_index(op.f('ix_olts_ip_address'), table_name='olts')
    op.drop_index(op.f('ix_olts_id'), table_name='olts')
    op.drop_table('olts')
    
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')