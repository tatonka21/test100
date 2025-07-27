import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import { agentApi, taskApi, healthApi, Agent, Task } from '../services/api';

interface DashboardStats {
  totalAgents: number;
  activeAgents: number;
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  runningTasks: number;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalAgents: 0,
    activeAgents: 0,
    totalTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    runningTasks: 0,
  });
  const [agents, setAgents] = useState<Agent[]>([]);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healthStatus, setHealthStatus] = useState<any>(null);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load agents
      const agentsData = await agentApi.getAgents();
      setAgents(agentsData);

      // Load recent tasks from all agents
      const allTasks: Task[] = [];
      for (const agent of agentsData) {
        try {
          const agentTasks = await taskApi.getAgentTasks(agent.id);
          allTasks.push(...agentTasks);
        } catch (err) {
          console.warn(`Failed to load tasks for agent ${agent.id}:`, err);
        }
      }

      // Sort tasks by creation date (most recent first)
      const sortedTasks = allTasks.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setRecentTasks(sortedTasks.slice(0, 10)); // Keep only 10 most recent

      // Calculate statistics
      const totalAgents = agentsData.length;
      const activeAgents = agentsData.filter(agent => 
        ['running', 'idle'].includes(agent.status)
      ).length;

      const totalTasks = allTasks.length;
      const completedTasks = allTasks.filter(task => task.status === 'completed').length;
      const failedTasks = allTasks.filter(task => task.status === 'failed').length;
      const runningTasks = allTasks.filter(task => task.status === 'running').length;

      setStats({
        totalAgents,
        activeAgents,
        totalTasks,
        completedTasks,
        failedTasks,
        runningTasks,
      });

      // Load health status
      try {
        const health = await healthApi.getHealth();
        setHealthStatus(health);
      } catch (err) {
        console.warn('Failed to load health status:', err);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
      case 'completed':
        return 'success';
      case 'failed':
      case 'error':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  const agentStatusData = agents.reduce((acc, agent) => {
    acc[agent.status] = (acc[agent.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const agentStatusChartData = Object.entries(agentStatusData).map(([status, count]) => ({
    name: status,
    value: count,
  }));

  const taskStatusData = [
    { name: 'Completed', value: stats.completedTasks },
    { name: 'Running', value: stats.runningTasks },
    { name: 'Failed', value: stats.failedTasks },
  ].filter(item => item.value > 0);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Agent Platform Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Agents
              </Typography>
              <Typography variant="h4">
                {stats.totalAgents}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {stats.activeAgents} active
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Tasks
              </Typography>
              <Typography variant="h4">
                {stats.totalTasks}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {stats.runningTasks} running
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Completed Tasks
              </Typography>
              <Typography variant="h4" color="success.main">
                {stats.completedTasks}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {stats.totalTasks > 0 ? Math.round((stats.completedTasks / stats.totalTasks) * 100) : 0}% success rate
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                System Health
              </Typography>
              <Typography variant="h4" color={healthStatus?.status === 'healthy' ? 'success.main' : 'error.main'}>
                {healthStatus?.status || 'Unknown'}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {healthStatus?.timestamp ? new Date(healthStatus.timestamp).toLocaleTimeString() : 'N/A'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Agent Status Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={agentStatusChartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {agentStatusChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Task Status Overview
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={taskStatusData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Tasks */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Tasks
          </Typography>
          {recentTasks.length === 0 ? (
            <Typography color="textSecondary">
              No tasks found
            </Typography>
          ) : (
            <Box>
              {recentTasks.map((task) => (
                <Box
                  key={task.id}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    py: 1,
                    borderBottom: '1px solid #333',
                  }}
                >
                  <Box>
                    <Typography variant="body1">
                      {task.task_type}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Agent: {task.agent_id.slice(0, 8)}... | {new Date(task.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                  <Chip
                    label={task.status}
                    color={getStatusColor(task.status) as any}
                    size="small"
                  />
                </Box>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default Dashboard;