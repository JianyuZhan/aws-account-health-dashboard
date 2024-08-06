// src/components/CurrentUser.js
import React from 'react';
import { Typography, Box } from '@mui/material';

// 写死的当前用户ID
const currentUser = 'jt@a.com';

// 获取当前用户ID的API
export const getCurrentUserId = () => currentUser;

const CurrentUser = () => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', marginLeft: 'auto', paddingRight: 2 }}>
      <Typography variant="body1">当前用户: {currentUser}</Typography>
    </Box>
  );
};

export default CurrentUser;
