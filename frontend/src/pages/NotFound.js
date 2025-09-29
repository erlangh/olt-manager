import React from 'react';
import { Result, Button } from 'antd';
import { useNavigate } from 'react-router-dom';

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="not-found-container">
      <Result
        status="404"
        title="404"
        subTitle="Maaf, halaman yang Anda cari tidak ditemukan."
        extra={
          <div>
            <Button type="primary" onClick={() => navigate('/dashboard')}>
              Kembali ke Dashboard
            </Button>
            <Button onClick={() => navigate(-1)} style={{ marginLeft: 8 }}>
              Kembali
            </Button>
          </div>
        }
      />
    </div>
  );
};

export default NotFound;