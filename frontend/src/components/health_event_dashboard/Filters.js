import React from 'react';
import Grid from '@mui/material/Grid';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';

// 过滤器渲染函数
const renderFilter = (label, name, value, handleFilterChange, options) => (
  <Grid item>
    <FormControl variant="outlined" size="small">
      <InputLabel>{label}</InputLabel>
      <Select
        name={name}
        value={value}
        onChange={handleFilterChange}
        label={label}
        style={{ minWidth: 150 }}
      >
        <MenuItem value="All">All</MenuItem>
        {options.map(option => (
          <MenuItem key={option} value={option}>{option}</MenuItem>
        ))}
      </Select>
    </FormControl>
  </Grid>
);

/*
Filters渲染多个下拉菜单用于筛选管理账户、事件类型等信息，并将选定的筛选条件通过 `handleFilterChange` 函数更新为 `filters` 状态。
*/
const Filters = ({ filters, allowedAccounts, handleFilterChange }) => (
  <Grid container spacing={2} alignItems="center">
    {renderFilter("Management Account", "managementAccount", filters.managementAccount, handleFilterChange, allowedAccounts)}
    {renderFilter("Event ARN", "eventArn", filters.eventArn, handleFilterChange, [])}
    {renderFilter("Event Type", "eventType", filters.eventType, handleFilterChange, [])}
    {renderFilter("Event Category", "eventCategory", filters.eventCategory, handleFilterChange, [])}
    {renderFilter("Event Status", "eventStatus", filters.eventStatus, handleFilterChange, [])}
    {renderFilter("Service", "service", filters.service, handleFilterChange, [])}
    {renderFilter("Region", "region", filters.region, handleFilterChange, [])}
  </Grid>
);

export default Filters;
