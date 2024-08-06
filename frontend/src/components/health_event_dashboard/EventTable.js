import React, { useState } from 'react';
import { IconButton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Collapse, Tooltip } from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import EventDetails from './EventDetails';
import { truncateString } from '../utils/helpers';

const EventTable = ({
  healthEvents,
  expandedEvent,
  showFullArn,
  eventDetails,
  failedEventArns,
  handleExpandClick,
  toggleArnDisplay,
  page
}) => {
  const [bedrockState, setBedrockState] = useState({});

  const handleBedrockQuery = (eventArn, state) => {
    setBedrockState(prevState => ({
      ...prevState,
      [eventArn]: state,
    }));
  };

  return (
    <TableContainer component={Paper} style={{ backgroundColor: '#f0f0f0' }}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Expand</TableCell>
            <TableCell>Account ID</TableCell>
            <TableCell>Event ARN</TableCell>
            <TableCell>Service</TableCell>
            <TableCell>Region</TableCell>
            <TableCell>Event Type Code</TableCell>
            <TableCell>Event Type Category</TableCell>
            <TableCell>Event Scope Code</TableCell>
            <TableCell>Availability Zone</TableCell>
            <TableCell>Start Time</TableCell>
            <TableCell>End Time</TableCell>
            <TableCell>Last Updated Time</TableCell>
            <TableCell>Status Code</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {healthEvents.slice((page - 1) * 10, page * 10).map((event) => (
            <React.Fragment key={event.EventArn}>
              <TableRow>
                <TableCell>
                  <IconButton onClick={() => handleExpandClick(event.EventArn)}>
                    {expandedEvent === event.EventArn ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                </TableCell>
                <TableCell>{event.AccountId}</TableCell>
                <TableCell>
                  <Tooltip title={event.EventArn} arrow>
                    <span onClick={() => toggleArnDisplay(event.EventArn)} style={{ cursor: 'pointer' }}>
                      {showFullArn[event.EventArn] ? event.EventArn : truncateString(event.EventArn, 30)}
                    </span>
                  </Tooltip>
                </TableCell>
                <TableCell>{event.Service}</TableCell>
                <TableCell>{event.Region}</TableCell>
                <TableCell>{event.EventTypeCode}</TableCell>
                <TableCell>{event.EventTypeCategory}</TableCell>
                <TableCell>{event.EventScopeCode}</TableCell>
                <TableCell>{event.AvailabilityZone}</TableCell>
                <TableCell>{event.StartTime}</TableCell>
                <TableCell>{event.EndTime}</TableCell>
                <TableCell>{event.LastUpdatedTime}</TableCell>
                <TableCell>{event.StatusCode}</TableCell>
              </TableRow>
              {expandedEvent === event.EventArn && (
                <TableRow>
                  <TableCell colSpan={13}>
                    <Collapse in={expandedEvent === event.EventArn} timeout="auto" unmountOnExit>
                      <EventDetails
                        eventArn={event.EventArn}
                        eventDetails={eventDetails}
                        failedEventArns={failedEventArns}
                        showFullArn={showFullArn}
                        toggleArnDisplay={toggleArnDisplay}
                        bedrockState={bedrockState[event.EventArn] || {}}
                        onBedrockQuery={handleBedrockQuery}
                      />
                    </Collapse>
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default EventTable;
