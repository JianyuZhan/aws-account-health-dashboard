import React, { useState } from 'react';
import { AppBar, Tabs, Tab, Toolbar } from '@mui/material';
import { Link, useLocation } from 'react-router-dom';
import CurrentUser from './CurrentUser';

const TopNav = () => {
  const location = useLocation(); // 获取当前路径位置
  const pathMap = {
    '/register_accounts': 0, 
    '/update_account': 1,
    '/deregister_accounts': 2,
    '/health_events': 3,
  };
  
  const currentTab = pathMap[location.pathname] || 0; // 根据当前路径获取对应的Tab索引

  const [value, setValue] = useState(currentTab); // 使用useState钩子来管理当前选中的Tab索引

  const handleChange = (event, newValue) => {
    setValue(newValue); // 当Tab改变时，更新当前选中的Tab索引
  };

  return (
    <AppBar position="static"> {/* 创建静态位置的AppBar */}
      <Toolbar>
        <Tabs value={value} onChange={handleChange} sx={{ flexGrow: 1 }}>
          <Tab 
            label="批量注册帐号" 
            component={Link} 
            to="/register_accounts" 
            sx={{ 
              color: value === 0 ? '#ffffff !important' : '#000000 !important',  
              // 当Tab被选中时（value === 0），文本颜色强制设置为白色，并使用 `!important` 防止被其他样式覆盖。
              // 当Tab未被选中时，文本颜色为黑色，并同样使用 `!important`。

              backgroundColor: value === 0 ? '#1976d2 !important' : 'inherit !important', 
              // 当Tab被选中时，背景颜色强制设置为蓝色，并使用 `!important` 防止被其他样式覆盖。
              // 当Tab未被选中时，背景颜色为继承颜色（透明），并同样使用 `!important`。
            }} 
          />
          <Tab 
            label="更新帐号" 
            component={Link} 
            to="/update_account" 
            sx={{ 
              color: value === 1 ? '#ffffff !important' : '#000000 !important', 
              backgroundColor: value === 1 ? '#1976d2 !important' : 'inherit !important', 
            }} 
          />
          <Tab 
            label="批量解绑帐号" 
            component={Link} 
            to="/deregister_accounts" 
            sx={{ 
              color: value === 2 ? '#ffffff !important' : '#000000 !important', 
              backgroundColor: value === 2 ? '#1976d2 !important' : 'inherit !important', 
            }} 
          />
          <Tab 
            label="健康事件" 
            component={Link} 
            to="/health_events" 
            sx={{ 
              color: value === 3 ? '#ffffff !important' : '#000000 !important', 
              backgroundColor: value === 3 ? '#1976d2 !important' : 'inherit !important', 
            }} 
          />
        </Tabs>
        <CurrentUser /> {/* 在导航栏右侧添加当前用户组件 */}
      </Toolbar>
    </AppBar>
  );
};

export default TopNav; // 导出TopNav组件以供其他组件使用