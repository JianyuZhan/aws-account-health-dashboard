import React from 'react';
import { Table, TableBody, TableCell, TableRow, Button, Box, Typography, CircularProgress } from '@mui/material';
import { formatValue } from '../utils/helpers';
import { queryBedrock } from '../utils/api';

const EventDetails = ({ eventArn, eventDetails, failedEventArns, bedrockState, onBedrockQuery }) => {
  const handleBedrockClick = async () => {
    if (eventDetails[eventArn] && eventDetails[eventArn].latest_description) {
      try {
        onBedrockQuery(eventArn, { loading: true, result: '', error: '' });

        const eventDesc = eventDetails[eventArn].latest_description;
        const affectedEntities = eventDetails[eventArn].affected_entities || [];

        const response = await queryBedrock(eventDesc, affectedEntities);

        if (response.error) {
          // 处理错误情况
          console.error("Error querying Bedrock:", response.message);
          onBedrockQuery(eventArn, { loading: false, result: '', error: response.message });
        } else {
          // 处理成功情况，直接使用返回的纯文本 result
          onBedrockQuery(eventArn, { loading: false, result: response.result, error: '' });
        }
      } catch (error) {
        console.error("Unexpected error querying Bedrock:", error);
        onBedrockQuery(eventArn, { loading: false, result: '', error: 'Unexpected error querying Bedrock.' });
      }
    }
    };

  const { loading, result, error } = bedrockState;

  return (
    <Table size="small" aria-label="event-details" style={{ backgroundColor: '#e0e0e0' }}>
      <TableBody>
        {/* 渲染事件详细信息 */}
        {eventDetails[eventArn] && Object.keys(eventDetails[eventArn]).map((key) => (
          <TableRow key={key}>
            <TableCell><b>{key}:</b></TableCell>
            <TableCell>{formatValue(eventDetails[eventArn][key])}</TableCell>
          </TableRow>
        ))}
        {/* 渲染失败原因，如果有的话 */}
        {failedEventArns[eventArn] && (
          <TableRow>
            <TableCell colSpan={2} style={{ color: 'red' }}>
              <b>Failure Reason:</b> {failedEventArns[eventArn]}
            </TableCell>
          </TableRow>
        )}
        {!failedEventArns[eventArn] && (
          <>
            {/* 添加 Bedrock 解读按钮，按钮在加载时禁用 */}
            <TableRow>
              <TableCell colSpan={2}>
                <Button variant="contained" onClick={handleBedrockClick} disabled={loading}>
                  Bedrock 解读
                </Button>
              </TableCell>
            </TableRow>
            {/* 显示 Bedrock 解读过程或结果 */}
            {(loading || result || error) && (
              <TableRow>
                <TableCell colSpan={2}>
                  <Box mt={2}>
                    {loading && (
                      <Box display="flex" alignItems="center">
                        <CircularProgress size={24} />
                        <Typography variant="body1" sx={{ ml: 2 }}>
                          询问 Bedrock 中...
                        </Typography>
                      </Box>
                    )}
                    {/* 成功！展示 Bedrock 结果 */}
                    {result && !loading && !error && (
                      result.split('\n').map((line, index) => (
                        <Typography
                          key={index}
                          variant="body1"
                          sx={{ fontWeight: 'bold', color: '#1a73e8' }}
                        >
                          {line}
                        </Typography>
                      ))
                    )}
                    {error && (
                      <Typography variant="body1" sx={{ color: 'red', fontWeight: 'bold' }}>
                        {error}
                      </Typography>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            )}
          </>
        )}
      </TableBody>
    </Table>
  );
};

export default EventDetails;
