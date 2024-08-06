import React, { useState } from 'react';
import { Button, Typography, Container, Box, Grid, Snackbar, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import config from '../../config';

const AfterRegister = () => {
  const [alert, setAlert] = useState({ open: false, severity: 'info', message: '', autoHideDuration: 6000 });
  const navigate = useNavigate();
  const location = useLocation();
  const registeredData = location.state?.registeredData || {};

  const handleRegisterAgain = () => {
    navigate('/register_accounts');
  };

  const handleFetchHealthEvents = () => {
    setAlert({ open: true, severity: 'info', message: '拉取健康事件中...', autoHideDuration: null });

    const accountIds = Object.keys(registeredData);

    fetch(`${config.API_ENDPOINT}/fetch_health_events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ account_ids: accountIds }),
    })
      .then(response => {
        if (!response.ok) {
          return response.text().then(text => {
            setAlert({ open: true, severity: 'error', message: `Error ${response.status}: ${text}`, autoHideDuration: 6000 });
            throw new Error(text);
          });
        }
        return response.json();
      })
      .then(data => {
        console.log('Health Events:', data);
        setAlert({ open: true, severity: 'success', message: '拉取成功', autoHideDuration: 6000 });
        navigate('/health_events'); // 跳转到健康事件展示页面
      })
      .catch(error => {
        console.error('Error:', error);
        setAlert({ open: true, severity: 'error', message: `拉取失败: ${error.message}`, autoHideDuration: 6000 });
      });
  };

  const handleCloseAlert = () => {
    setAlert({ ...alert, open: false });
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          注册成功
        </Typography>
        <Typography variant="h6">以下是刚才注册的帐户信息:</Typography>

        <TableContainer component={Paper} sx={{ my: 2 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>帐号</TableCell>
                <TableCell>跨账户角色</TableCell>
                <TableCell>允许的用户</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.keys(registeredData).map((accountId) => (
                <TableRow key={accountId}>
                  <TableCell>{accountId}</TableCell>
                  <TableCell>{registeredData[accountId].cross_account_role}</TableCell>
                  <TableCell>
                    {Object.keys(registeredData[accountId].allowed_users).length > 0 ? (
                      <Table>
                        <TableHead>
                          <TableRow>
                            <TableCell>用户邮箱</TableCell>
                            <TableCell>用户名</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {Object.entries(registeredData[accountId].allowed_users).map(([email, name]) => (
                            <TableRow key={email}>
                              <TableCell>{email}</TableCell>
                              <TableCell>{name}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : (
                      '无'
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        <Grid container spacing={2} justifyContent="flex-end">
          <Grid item>
            <Button variant="contained" color="primary" onClick={handleRegisterAgain}>
              注册帐户
            </Button>
          </Grid>
          <Grid item>
            <Button variant="contained" color="secondary" onClick={handleFetchHealthEvents}>
              拉取健康事件
            </Button>
          </Grid>
        </Grid>
      </Box>
      <Snackbar 
        open={alert.open} 
        onClose={handleCloseAlert} 
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }} 
        autoHideDuration={alert.autoHideDuration}
      >
        <Alert onClose={handleCloseAlert} severity={alert.severity} sx={{ width: '100%' }}>
          {alert.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default AfterRegister;
