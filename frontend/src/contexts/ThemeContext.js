import React, { createContext, useContext, useState, useEffect } from 'react';
import { ConfigProvider, theme as antdTheme } from 'antd';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    // Get theme from localStorage or default to 'light'
    const savedTheme = localStorage.getItem('theme');
    return savedTheme || 'light';
  });

  // Update localStorage when theme changes
  useEffect(() => {
    localStorage.setItem('theme', theme);
    
    // Update document class for CSS variables
    document.documentElement.setAttribute('data-theme', theme);
    
    // Update body class for compatibility
    document.body.className = theme === 'dark' ? 'dark-theme' : 'light-theme';
  }, [theme]);

  // Toggle between light and dark theme
  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'light' ? 'dark' : 'light');
  };

  // Set specific theme
  const setSpecificTheme = (newTheme) => {
    if (newTheme === 'light' || newTheme === 'dark') {
      setTheme(newTheme);
    }
  };

  // Get Ant Design theme configuration
  const getAntdTheme = () => {
    return {
      algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      token: {
        colorPrimary: '#1890ff',
        colorSuccess: '#52c41a',
        colorWarning: '#faad14',
        colorError: '#ff4d4f',
        colorInfo: '#1890ff',
        borderRadius: 6,
        wireframe: false,
        ...(theme === 'dark' ? {
          colorBgContainer: '#141414',
          colorBgElevated: '#1f1f1f',
          colorBgLayout: '#000000',
          colorBorder: '#303030',
          colorBorderSecondary: '#262626',
          colorText: 'rgba(255, 255, 255, 0.85)',
          colorTextSecondary: 'rgba(255, 255, 255, 0.65)',
          colorTextTertiary: 'rgba(255, 255, 255, 0.45)',
          colorTextQuaternary: 'rgba(255, 255, 255, 0.25)',
        } : {
          colorBgContainer: '#ffffff',
          colorBgElevated: '#ffffff',
          colorBgLayout: '#f5f5f5',
          colorBorder: '#d9d9d9',
          colorBorderSecondary: '#f0f0f0',
          colorText: 'rgba(0, 0, 0, 0.88)',
          colorTextSecondary: 'rgba(0, 0, 0, 0.65)',
          colorTextTertiary: 'rgba(0, 0, 0, 0.45)',
          colorTextQuaternary: 'rgba(0, 0, 0, 0.25)',
        })
      },
      components: {
        Layout: {
          headerBg: theme === 'dark' ? '#001529' : '#ffffff',
          siderBg: theme === 'dark' ? '#001529' : '#ffffff',
          bodyBg: theme === 'dark' ? '#000000' : '#f5f5f5',
        },
        Menu: {
          darkItemBg: '#001529',
          darkSubMenuItemBg: '#000c17',
          darkItemSelectedBg: '#1890ff',
          darkItemHoverBg: '#112545',
        },
        Card: {
          headerBg: theme === 'dark' ? '#1f1f1f' : '#fafafa',
        },
        Table: {
          headerBg: theme === 'dark' ? '#1f1f1f' : '#fafafa',
          rowHoverBg: theme === 'dark' ? '#262626' : '#f5f5f5',
        },
        Button: {
          primaryShadow: '0 2px 0 rgba(5, 145, 255, 0.1)',
        },
        Input: {
          hoverBorderColor: '#40a9ff',
          focusBorderColor: '#1890ff',
        },
        Select: {
          hoverBorderColor: '#40a9ff',
          focusBorderColor: '#1890ff',
        },
      }
    };
  };

  // Get CSS custom properties for the current theme
  const getCSSVariables = () => {
    if (theme === 'dark') {
      return {
        '--primary-color': '#1890ff',
        '--success-color': '#52c41a',
        '--warning-color': '#faad14',
        '--error-color': '#ff4d4f',
        '--info-color': '#1890ff',
        '--bg-color': '#000000',
        '--bg-container': '#141414',
        '--bg-elevated': '#1f1f1f',
        '--border-color': '#303030',
        '--border-color-secondary': '#262626',
        '--text-color': 'rgba(255, 255, 255, 0.85)',
        '--text-color-secondary': 'rgba(255, 255, 255, 0.65)',
        '--text-color-tertiary': 'rgba(255, 255, 255, 0.45)',
        '--shadow-color': 'rgba(0, 0, 0, 0.45)',
        '--header-bg': '#001529',
        '--sider-bg': '#001529',
      };
    } else {
      return {
        '--primary-color': '#1890ff',
        '--success-color': '#52c41a',
        '--warning-color': '#faad14',
        '--error-color': '#ff4d4f',
        '--info-color': '#1890ff',
        '--bg-color': '#f5f5f5',
        '--bg-container': '#ffffff',
        '--bg-elevated': '#ffffff',
        '--border-color': '#d9d9d9',
        '--border-color-secondary': '#f0f0f0',
        '--text-color': 'rgba(0, 0, 0, 0.88)',
        '--text-color-secondary': 'rgba(0, 0, 0, 0.65)',
        '--text-color-tertiary': 'rgba(0, 0, 0, 0.45)',
        '--shadow-color': 'rgba(0, 0, 0, 0.15)',
        '--header-bg': '#ffffff',
        '--sider-bg': '#ffffff',
      };
    }
  };

  // Apply CSS variables to document root
  useEffect(() => {
    const variables = getCSSVariables();
    const root = document.documentElement;
    
    Object.entries(variables).forEach(([property, value]) => {
      root.style.setProperty(property, value);
    });
  }, [theme]);

  const value = {
    theme,
    toggleTheme,
    setTheme: setSpecificTheme,
    isDark: theme === 'dark',
    isLight: theme === 'light',
    getAntdTheme,
    getCSSVariables
  };

  return (
    <ThemeContext.Provider value={value}>
      <ConfigProvider theme={getAntdTheme()}>
        {children}
      </ConfigProvider>
    </ThemeContext.Provider>
  );
};