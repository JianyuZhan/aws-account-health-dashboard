// src/components/TopNav.js
import React from 'react';
import { AppBar, Tabs, Tab } from '@mui/material';
import { Link } from 'react-router-dom';

const TopNav = () => {
  return (
    <AppBar position="static">
      <Tabs>
        <Tab label="批量注册帐号" component={Link} to="/register_accounts" />
        <Tab label="更新帐号" component={Link} to="/update_account" />
        <Tab label="批量解绑帐号" component={Link} to="/deregister_accounts" />
      </Tabs>
    </AppBar>
  );
};

export default TopNav;
