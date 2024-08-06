// src/components/Sidebar.js
import React from 'react';
import { Drawer, List, ListItem, ListItemText, ListItemIcon } from '@mui/material';
import { Link } from 'react-router-dom';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import UpdateIcon from '@mui/icons-material/Update';
import DeleteIcon from '@mui/icons-material/Delete';

const Sidebar = () => {
  return (
    <Drawer variant="permanent" sx={{ width: 240, flexShrink: 0 }}>
      <List sx={{ width: 240 }}>
        <ListItem button component={Link} to="/register_accounts">
          <ListItemIcon><AccountCircleIcon /></ListItemIcon>
          <ListItemText primary="批量注册帐号" />
        </ListItem>
        <ListItem button component={Link} to="/update_account">
          <ListItemIcon><UpdateIcon /></ListItemIcon>
          <ListItemText primary="更新帐号" />
        </ListItem>
        <ListItem button component={Link} to="/deregister_accounts">
          <ListItemIcon><DeleteIcon /></ListItemIcon>
          <ListItemText primary="批量解绑帐号" />
        </ListItem>
      </List>
    </Drawer>
  );
};

export default Sidebar;
