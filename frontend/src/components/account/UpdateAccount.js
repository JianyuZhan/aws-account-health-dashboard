import React, { useState } from 'react';
import { TextField, Button, Typography, Container, Box, Grid, IconButton, Card, CardContent, CardActions, Snackbar, Alert } from '@mui/material';
import { Add as AddIcon, Remove as RemoveIcon } from '@mui/icons-material';
import config from '../../config';

const UpdateAccount = () => {
  const [accountId, setAccountId] = useState('');
  const [addUsers, setAddUsers] = useState([{ email: '', name: '' }]);
  const [deleteUsers, setDeleteUsers] = useState([{ email: '' }]);
  const [updateUsers, setUpdateUsers] = useState([{ email: '', name: '' }]);
  const [errors, setErrors] = useState({});
  const [alert, setAlert] = useState({ open: false, severity: 'info', message: '', autoHideDuration: 6000 });

  const handleAddUserChange = (index, event) => {
    const { name, value } = event.target;
    const newUsers = [...addUsers];
    newUsers[index][name] = value;
    setAddUsers(newUsers);
  };

  const handleDeleteUserChange = (index, event) => {
    const { name, value } = event.target;
    const newUsers = [...deleteUsers];
    newUsers[index][name] = value;
    setDeleteUsers(newUsers);
  };

  const handleUpdateUserChange = (index, event) => {
    const { name, value } = event.target;
    const newUsers = [...updateUsers];
    newUsers[index][name] = value;
    setUpdateUsers(newUsers);
  };

  const handleAddUserAdd = () => {
    setAddUsers([...addUsers, { email: '', name: '' }]);
  };

  const handleDeleteUserAdd = () => {
    setDeleteUsers([...deleteUsers, { email: '' }]);
  };

  const handleUpdateUserAdd = () => {
    setUpdateUsers([...updateUsers, { email: '', name: '' }]);
  };

  const handleAddUserRemove = (index) => {
    const newUsers = addUsers.filter((_, i) => i !== index);
    setAddUsers(newUsers);
  };

  const handleDeleteUserRemove = (index) => {
    const newUsers = deleteUsers.filter((_, i) => i !== index);
    setDeleteUsers(newUsers);
  };

  const handleUpdateUserRemove = (index) => {
    const newUsers = updateUsers.filter((_, i) => i !== index);
    setUpdateUsers(newUsers);
  };

  const validateFields = () => {
    const newErrors = {};
    if (!accountId) {
      newErrors.accountId = '帐号 ID 是必填项';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleUpdate = () => {
    if (!validateFields()) {
      console.log('Validation failed');
      return;
    }

    setAlert({ open: true, severity: 'info', message: '更新中...', autoHideDuration: null });

    const params = {
      add: addUsers.reduce((acc, user) => {
        if (user.email && user.name) {
          acc[user.email] = user.name;
        }
        return acc;
      }, {}),
      delete: deleteUsers.reduce((acc, user) => {
        if (user.email) {
          acc[user.email] = null;
        }
        return acc;
      }, {}),
      update: updateUsers.reduce((acc, user) => {
        if (user.email && user.name) {
          acc[user.email] = user.name;
        }
        return acc;
      }, {})
    };

    const body = {
      account_id: accountId,
      params: params
    };

    console.log('Sending request to API:', config.API_ENDPOINT);
    console.log('Request body:', JSON.stringify(body));

    fetch(`${config.API_ENDPOINT}/update_account`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })
    .then(response => {
      console.log('Response status:', response.status);
      console.log('Response status text:', response.statusText);
      if (!response.ok) {
        return response.text().then(text => {
          setAlert({ open: true, severity: 'error', message: `Error ${response.status}: ${text}`, autoHideDuration: 6000 });
          throw new Error(text);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log('Response from API:', data);
      setAlert({ open: true, severity: 'success', message: '更新成功', autoHideDuration: 6000 });
    })
    .catch(error => {
      console.error('Error:', error);
      setAlert({ open: true, severity: 'error', message: `更新失败: ${error.message}`, autoHideDuration: 6000 });
    });
  };

  const handleCloseAlert = () => {
    setAlert({ ...alert, open: false });
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          更新组织帐号
        </Typography>
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={11}>
                <TextField
                  label="帐号 ID"
                  name="accountId"
                  variant="outlined"
                  fullWidth
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  error={!!errors.accountId}
                  helperText={errors.accountId}
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Grid container alignItems="center">
              <Grid item>
                <IconButton color="primary" onClick={handleAddUserAdd}>
                  <AddIcon />
                </IconButton>
              </Grid>
              <Grid item>
                <Typography variant="h6" gutterBottom>
                  添加用户
                </Typography>
              </Grid>
            </Grid>
            {addUsers.map((user, index) => (
              <Grid container spacing={2} alignItems="center" key={index}>
                <Grid item xs={5}>
                  <TextField
                    label="用户邮箱"
                    name="email"
                    variant="outlined"
                    fullWidth
                    value={user.email}
                    onChange={(e) => handleAddUserChange(index, e)}
                  />
                </Grid>
                <Grid item xs={5}>
                  <TextField
                    label="用户名"
                    name="name"
                    variant="outlined"
                    fullWidth
                    value={user.name}
                    onChange={(e) => handleAddUserChange(index, e)}
                  />
                </Grid>
                <Grid item xs={2}>
                  <IconButton color="secondary" onClick={() => handleAddUserRemove(index)}>
                    <RemoveIcon />
                  </IconButton>
                </Grid>
              </Grid>
            ))}
          </CardContent>
        </Card>
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Grid container alignItems="center">
              <Grid item>
                <IconButton color="primary" onClick={handleDeleteUserAdd}>
                  <AddIcon />
                </IconButton>
              </Grid>
              <Grid item>
                <Typography variant="h6" gutterBottom>
                  删除用户
                </Typography>
              </Grid>
            </Grid>
            {deleteUsers.map((user, index) => (
              <Grid container spacing={2} alignItems="center" key={index}>
                <Grid item xs={10}>
                  <TextField
                    label="用户邮箱"
                    name="email"
                    variant="outlined"
                    fullWidth
                    value={user.email}
                    onChange={(e) => handleDeleteUserChange(index, e)}
                  />
                </Grid>
                <Grid item xs={2}>
                  <IconButton color="secondary" onClick={() => handleDeleteUserRemove(index)}>
                    <RemoveIcon />
                  </IconButton>
                </Grid>
              </Grid>
            ))}
          </CardContent>
        </Card>
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Grid container alignItems="center">
              <Grid item>
                <IconButton color="primary" onClick={handleUpdateUserAdd}>
                  <AddIcon />
                </IconButton>
              </Grid>
              <Grid item>
                <Typography variant="h6" gutterBottom>
                  更新用户
                </Typography>
              </Grid>
            </Grid>
            {updateUsers.map((user, index) => (
              <Grid container spacing={2} alignItems="center" key={index}>
                <Grid item xs={5}>
                  <TextField
                    label="用户邮箱"
                    name="email"
                    variant="outlined"
                    fullWidth
                    value={user.email}
                    onChange={(e) => handleUpdateUserChange(index, e)}
                  />
                </Grid>
                <Grid item xs={5}>
                  <TextField
                    label="用户名"
                    name="name"
                    variant="outlined"
                    fullWidth
                    value={user.name}
                    onChange={(e) => handleUpdateUserChange(index, e)}
                  />
                </Grid>
                <Grid item xs={2}>
                  <IconButton color="secondary" onClick={() => handleUpdateUserRemove(index)}>
                    <RemoveIcon />
                  </IconButton>
                </Grid>
              </Grid>
            ))}
          </CardContent>
        </Card>
        <CardActions>
          <Grid container spacing={2} justifyContent="flex-end">
            <Grid item>
              <Button variant="contained" color="primary" onClick={handleUpdate}>
                更新帐号
              </Button>
            </Grid>
          </Grid>
        </CardActions>
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

export default UpdateAccount;