import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Types
export interface Agent {
  id: string;
  name: string;
  description?: string;
  type: string;
  capabilities: string[];
  resources: Record<string, any>;
  parameters?: Record<string, any>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AgentConfig {
  name: string;
  description?: string;
  type: string;
  capabilities: string[];
  resources: Record<string, any>;
  parameters?: Record<string, any>;
}

export interface Task {
  id: string;
  agent_id: string;
  task_type: string;
  parameters: Record<string, any>;
  status: string;
  result?: Record<string, any>;
  error_message?: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface TaskCreate {
  agent_id: string;
  task_type: string;
  parameters: Record<string, any>;
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  service: string;
  database?: string;
  error?: string;
}

// Agent API
export const agentApi = {
  // Get all agents
  getAgents: async (): Promise<Agent[]> => {
    const response = await api.get('/agents');
    return response.data;
  },

  // Get agent by ID
  getAgent: async (id: string): Promise<Agent> => {
    const response = await api.get(`/agents/${id}`);
    return response.data;
  },

  // Create new agent
  createAgent: async (config: AgentConfig): Promise<Agent> => {
    const response = await api.post('/agents', config);
    return response.data;
  },

  // Delete agent
  deleteAgent: async (id: string): Promise<void> => {
    await api.delete(`/agents/${id}`);
  },

  // Update agent status
  updateAgentStatus: async (id: string, status: string): Promise<Agent> => {
    const response = await api.put(`/agents/${id}/status`, { status });
    return response.data;
  },
};

// Task API
export const taskApi = {
  // Get all tasks for an agent
  getAgentTasks: async (agentId: string): Promise<Task[]> => {
    const response = await api.get(`/agents/${agentId}/tasks`);
    return response.data;
  },

  // Get task by ID
  getTask: async (id: string): Promise<Task> => {
    const response = await api.get(`/tasks/${id}`);
    return response.data;
  },

  // Create new task
  createTask: async (task: TaskCreate): Promise<Task> => {
    const response = await api.post('/tasks', task);
    return response.data;
  },
};

// Health API
export const healthApi = {
  // Get API Gateway health
  getHealth: async (): Promise<HealthStatus> => {
    const response = await api.get('/health');
    return response.data;
  },

  // Get service-specific health
  getServiceHealth: async (service: string): Promise<HealthStatus> => {
    const serviceUrls = {
      'agent-manager': 'http://localhost:8000/health',
      'agent-runtime': 'http://localhost:8001/health',
    };
    
    const url = serviceUrls[service as keyof typeof serviceUrls];
    if (!url) {
      throw new Error(`Unknown service: ${service}`);
    }
    
    const response = await axios.get(url);
    return response.data;
  },
};

// Metrics API
export const metricsApi = {
  // Get metrics from services
  getMetrics: async (service: string): Promise<string> => {
    const serviceUrls = {
      'api-gateway': 'http://localhost:8080/metrics',
      'agent-manager': 'http://localhost:8000/metrics',
      'agent-runtime': 'http://localhost:8001/metrics',
    };
    
    const url = serviceUrls[service as keyof typeof serviceUrls];
    if (!url) {
      throw new Error(`Unknown service: ${service}`);
    }
    
    const response = await axios.get(url, {
      headers: { 'Accept': 'text/plain' }
    });
    return response.data;
  },
};

// WebSocket connection for real-time updates
export class WebSocketService {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Function[]> = new Map();

  connect() {
    const wsUrl = `ws://localhost:8080/ws`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.type;
        const listeners = this.listeners.get(eventType) || [];
        listeners.forEach(listener => listener(data));
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      // Attempt to reconnect after 5 seconds
      setTimeout(() => this.connect(), 5000);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  subscribe(eventType: string, callback: Function) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(callback);
  }

  unsubscribe(eventType: string, callback: Function) {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }
}

export const wsService = new WebSocketService();

export default api;