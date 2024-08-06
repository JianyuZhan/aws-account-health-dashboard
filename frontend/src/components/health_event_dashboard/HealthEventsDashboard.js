import React, { useState, useEffect, useCallback } from 'react';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import RefreshIcon from '@mui/icons-material/Refresh';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';

import { getAllowedAccounts, getHealthEvents, getEventDetails } from '../utils/api';
import Filters from './Filters';
import EventTable from './EventTable';
import PaginationComponent from './PaginationComponent';

const HealthEventsDashboard = () => {
    const [eventDetails, setEventDetails] = useState({});
    const [failedEventArns, setFailedEventArns] = useState({});
    const [healthEvents, setHealthEvents] = useState([]);
    const [loadedPages, setLoadedPages] = useState([]); // 保存已经加载的页码
    const [expandedEvent, setExpandedEvent] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [showFullArn, setShowFullArn] = useState({});
    const [filters, setFilters] = useState({
      managementAccount: 'All',
      eventArn: 'All',
      eventType: 'All',
      eventCategory: 'All',
      eventStatus: 'All',
      service: 'All',
      region: 'All'
    });
    const [allowedAccounts, setAllowedAccounts] = useState([]);

    const handleExpandClick = (eventArn) => {
        setExpandedEvent(expandedEvent === eventArn ? null : eventArn);
    };

    // 实现 toggleArnDisplay 函数
    const toggleArnDisplay = (eventArn) => {
        setShowFullArn((prev) => ({
            ...prev,
            [eventArn]: !prev[eventArn]
        }));
    };

    // 获取允许访问的账户
    const refreshAllowedAccounts = useCallback(async () => {
        try {
          setSuccessMessage('正在获取当前用户所允许访问的帐号...');
          const accounts = await getAllowedAccounts();
          setAllowedAccounts(accounts);
          setSuccessMessage('获取当前用户所允许访问的帐号成功！');
        } catch (error) {
          setErrorMessage(error.message || '获取当前用户所允许访问的帐号失败');
        }
    }, []);
      
    const generateEventFilter = (filters) => {
        const eventFilter = {};
      
        if (filters.eventArn && filters.eventArn !== 'All') {
          eventFilter.EventArn = [filters.eventArn];
        }
        if (filters.eventType && filters.eventType !== 'All') {
          eventFilter.EventTypeCode = [filters.eventType];
        }
        if (filters.eventCategory && filters.eventCategory !== 'All') {
          eventFilter.EventTypeCategory = [filters.eventCategory];
        }
        if (filters.eventStatus && filters.eventStatus !== 'All') {
          eventFilter.EventStatus = [filters.eventStatus];
        }
        if (filters.service && filters.service !== 'All') {
          eventFilter.Service = [filters.service];
        }
        if (filters.region && filters.region !== 'All') {
          eventFilter.Region = [filters.region];
        }
      
        return Object.keys(eventFilter).length > 0 ? eventFilter : null;
    };
      
    // 刷新事件列表
    const refreshHealthEvents = useCallback(async () => {
        try {
            // 如果filters.managementAccount值为'All'，表示所有允许的账户
            const selectedAccounts = filters.managementAccount === 'All'
                ? allowedAccounts
                : [filters.managementAccount];
    
            // 基于当前Filters组件的值，生成api需要的eventFilter
            const eventFilter = generateEventFilter(filters);
    
            // 调用 getHealthEvents API
            setSuccessMessage('正在获取健康事件列表...');
            const eventsResponse = await getHealthEvents(selectedAccounts, eventFilter);
            setSuccessMessage(`获取健康事件成功！共${eventsResponse.data.all_events.length}个事件!`);

            setHealthEvents(eventsResponse.data.all_events);
            setTotalPages(Math.ceil(eventsResponse.data.all_events.length / 10));
            setPage(1); // 第一页
    
            // 获取第一页的事件详情
            const firstPageEventArns = eventsResponse.data.all_events.slice(0, 10).map(event => event.EventArn);

            if (!loadedPages.includes(1)) {  // 只在页面未加载过的情况下加载事件详情
                setSuccessMessage('正在获取事件详情...');
                const { eventDetails, failedEventArns } = await getEventDetails(firstPageEventArns);
                setSuccessMessage(`获取事件详情成功！`);

                setEventDetails(prevDetails => ({...prevDetails, ...eventDetails}));
                setFailedEventArns(prevFailures => ({...prevFailures, ...failedEventArns}));
                setLoadedPages(prevPages => [...prevPages, 1]);
            }
            setSuccessMessage('事件列表刷新成功');
        } catch (error) {
            setErrorMessage('刷新事件列表失败: ' + (error.message || '未知错误'));
        }
    }, [filters, allowedAccounts, loadedPages]);

    // 页面加载时获取账户
    useEffect(() => {
        refreshAllowedAccounts();
    }, [refreshAllowedAccounts]);

    // 处理筛选条件变化
    const handleFilterChange = (event) => {
        const { name, value } = event.target;
        setFilters(prevFilters => ({
            ...prevFilters,
            [name]: value
        }));
    };

    // 处理分页变化
    const handlePageChange = async (event, thisPage) => {
        setPage(thisPage);

        if (!loadedPages.includes(thisPage)) { // 只在页面未加载过的情况下加载事件详情
            const startIndex = (thisPage - 1) * 10;
            const endIndex = startIndex + 10;
            const currentEvents = healthEvents.slice(startIndex, endIndex);
            const eventArns = currentEvents.map(event => event.EventArn);

            try {
                setSuccessMessage('正在获取事件详情...');
                const { eventDetails, failedEventArns } = await getEventDetails(eventArns);
                setSuccessMessage(`获取事件详情成功！`);

                setEventDetails(prevDetails => ({...prevDetails, ...eventDetails}));
                setFailedEventArns(prevFailures => ({...prevFailures, ...failedEventArns}));
                setLoadedPages(prevPages => [...prevPages, thisPage]);
            } catch (error) {
                setErrorMessage('加载事件详情失败');
            }
        }
    };

    const handleCloseSnackbar = () => {
        setErrorMessage('');
        setSuccessMessage('');
    };

    return (
        <Grid container spacing={2}>
            <Grid item xs={12}>
                <Typography variant="h4" align="center" gutterBottom>
                    AWS Health Events Dashboard
                </Typography>
            </Grid>
            <Grid item xs={12}>
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Filters 
                        filters={filters}
                        allowedAccounts={allowedAccounts}
                        handleFilterChange={handleFilterChange}
                    />
                    <IconButton onClick={refreshAllowedAccounts}>
                        <RefreshIcon />
                    </IconButton>
                </Box>
            </Grid>
            <Grid item xs={12}>
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Typography variant="h6">
                        事件列表
                    </Typography>
                    <IconButton onClick={refreshHealthEvents}>
                        <RefreshIcon />
                    </IconButton>
                </Box>
                <EventTable
                    healthEvents={healthEvents}
                    expandedEvent={expandedEvent}
                    eventDetails={eventDetails}
                    failedEventArns={failedEventArns}
                    handleExpandClick={handleExpandClick}
                    toggleArnDisplay={toggleArnDisplay} // 传递 toggleArnDisplay 函数
                    showFullArn={showFullArn} // 传递 showFullArn 状态
                    page={page}
                />
                <PaginationComponent
                    totalPages={totalPages}
                    page={page}
                    handlePageChange={handlePageChange}
                />
            </Grid>
            <Snackbar
                open={!!errorMessage || !!successMessage}
                autoHideDuration={6000}
                onClose={handleCloseSnackbar}
                anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            >
                <Alert onClose={handleCloseSnackbar} severity={errorMessage ? 'error' : 'success'}>
                    {errorMessage || successMessage}
                </Alert>
            </Snackbar>
        </Grid>
    );
};

export default HealthEventsDashboard;