import axios from 'axios';
import config from '../../config';
import { getCurrentUserId } from '../CurrentUser';
import { XMLParser } from 'fast-xml-parser';

export const postData = async (url, data) => {
  console.log(`POST request to ${url} with data: ${JSON.stringify(data)}`);
  return await axios.post(url, data);
};

export const getAllowedAccounts = async () => {
    try {
      console.log('Calling getAllowedAccounts');
      const response = await postData(`${config.API_ENDPOINT}/get_allowed_accounts`, { user_id: getCurrentUserId() });
      const accounts = response.data.allowed_accounts.map(account => account.AccountId);
      console.log('getAllowedAccounts succeeded!');
      return accounts;
    } catch (error) {
      console.error('Error querying allowed accounts', error);
      throw new Error('获取当前用户所允许访问的帐号失败');
    }
};  

export const getHealthEvents = async (selectedAccounts = [], eventFilter) => {
    console.log('Querying health events with eventFilter ', eventFilter, ', selectedAccounts:', selectedAccounts);
  
    // 如果 selectedAccounts 为空，抛出错误
    if (!selectedAccounts || selectedAccounts.length === 0) {
      throw new Error('No accounts selected for querying health events.');
    }
  
    const accountsObject = selectedAccounts.reduce((acc, accountId) => {
      acc[accountId] = {
        cross_account_role: 'DataCollectionCrossAccountRole',
        event_filter: eventFilter || {},
      };
      return acc;
    }, {});
  
    try {
      const response = await axios.post(`${config.API_ENDPOINT}/query_health_events`, {
        user_id: getCurrentUserId(),
        accounts: accountsObject
      });
  
      console.log(`Health events received: ${JSON.stringify(response.data.all_events)}`);
  
      if (response.data && response.data.all_events.length > 0) {
        return response;
      } else {
        throw new Error('No health events found.');
      }
    } catch (error) {
      console.error('Error querying health events', error);
      throw error;
    }
  };  

  export const getEventDetails = async (eventArns) => {
    try {
      const response = await axios.post(`${config.API_ENDPOINT}/query_event_details`, {
        event_arns: eventArns
      });
  
      console.log(`Event details received: ${JSON.stringify(response.data.event_details)}`);
      console.log(`Failed event arns received: ${JSON.stringify(response.data.failed_event_arns)}`);
  
      return {
        eventDetails: mapEventDetails(response.data.event_details),
        failedEventArns: mapFailedEventArns(response.data.failed_event_arns),
      };
    } catch (error) {
      console.error('Error querying event details', error);
      throw error;
    }
};

const mapEventDetails = (details) => {
  return details.reduce((acc, detail) => {
    acc[detail.event_arn] = detail;
    return acc;
  }, {});
};

const mapFailedEventArns = (failedEvents) => {
  return failedEvents.reduce((acc, failure) => {
    acc[failure.event_arn] = failure.reason;
    return acc;
  }, {});
};

export const queryBedrock = async (eventDesc, affectedEntities = []) => {
  try {
    const requestData = {
      event_desc: eventDesc,
      affected_entities: affectedEntities,
    };

    console.log('Calling queryBedrock with data:', requestData);

    const response = await axios.post(`${config.API_ENDPOINT}/query_bedrock`, requestData);

    console.log(`queryBedrock response received: ${JSON.stringify(response.data)}`);

    const { status, data } = response;

    if (status === 200) {
      const resultString = data.result || "";

      console.log("Raw XML result:", resultString);

      // 使用 fast-xml-parser 解析 XML
      const parser = new XMLParser();
      const parsedResult = parser.parse(resultString);

      console.log("Parsed XML result:", parsedResult);

      // 将解析后的结果转换为纯文本
      const textResult = formatXmlToText(parsedResult);

      console.log("Formatted text result:", textResult);

      return { error: false, result: textResult };
    } else {
      const errorMessage = data.message || '未知错误';
      console.error('Bedrock API returned an error:', errorMessage);
      return { error: true, message: errorMessage };
    }
  } catch (error) {
    console.error('Error querying Bedrock', error);

    const errorMessage = error.response?.data?.message || '查询Bedrock API失败';
    return { error: true, message: errorMessage };
  }
};

// 将解析后的 XML 对象转换为纯文本
function formatXmlToText(parsedXml) {
  let text = '';

  if (parsedXml.Output) {
    if (parsedXml.Output.Summary) {
      text += 'Summary:\n' + parsedXml.Output.Summary + '\n\n';
    }
    if (parsedXml.Output.Action) {
      text += 'Action:\n' + parsedXml.Output.Action + '\n\n';
    }
  }

  console.log("Generated text from XML:", text);
  
  return text.trim();
}