const { createApp, ref, computed } = Vue
const { createRouter, createWebHistory } = VueRouter

const API_BASE_URL = 'http://localhost:5001'

// Component imports
const DashboardComponent = {
    template: await fetch(`${API_BASE_URL}/static/templates/dashboard.html`).then(response => response.text()),
    props: ['applications', 'verifiedCount', 'pendingCount']
}

const ApplicationsComponent = {
    template: await fetch(`${API_BASE_URL}/static/templates/applications.html`).then(response => response.text()),
    setup(props, { emit }) {
        const showAddModal = ref(false)
        const newApp = ref({ name: '', owner: '', web_ui: '', db_port: null })
        
        const handleFileUpload = async (event) => {
            const file = event.target.files[0]
            if (file) {
                const formData = new FormData()
                formData.append('file', file)
                try {
                    await axios.post(`${API_BASE_URL}/api/applications/import`, formData, {
                        headers: {
                            'Content-Type': 'multipart/form-data'
                        }
                    })
                    emit('refresh')
                } catch (error) {
                    console.error('Error importing applications:', error)
                }
            }
        }

        const addApplication = async () => {
            try {
                await axios.post(`${API_BASE_URL}/api/applications`, newApp.value)
                emit('refresh')
                showAddModal.value = false
                newApp.value = { name: '', owner: '', web_ui: '', db_port: null }
            } catch (error) {
                console.error('Error adding application:', error)
            }
        }

        const getStatusClass = (status) => {
            switch (status) {
                case 'active':
                    return 'bg-green-100 text-green-800'
                case 'shutdown_pending':
                    return 'bg-yellow-100 text-yellow-800'
                case 'shutdown_verified':
                    return 'bg-blue-100 text-blue-800'
                default:
                    return 'bg-gray-100 text-gray-800'
            }
        }

        return {
            showAddModal,
            newApp,
            handleFileUpload,
            addApplication,
            getStatusClass
        }
    },
    props: ['applications']
}

const ServersComponent = {
    template: await fetch(`${API_BASE_URL}/static/templates/servers.html`).then(response => response.text()),
    setup(props, { emit }) {
        const showAddServerModal = ref(false)
        const newServer = ref({ hostname: '', ip_address: '', app_id: null })
        
        const handleFileUpload = async (event) => {
            const file = event.target.files[0]
            if (file) {
                const formData = new FormData()
                formData.append('file', file)
                try {
                    await axios.post(`${API_BASE_URL}/api/servers/import`, formData, {
                        headers: {
                            'Content-Type': 'multipart/form-data'
                        }
                    })
                    emit('refresh')
                } catch (error) {
                    console.error('Error importing servers:', error)
                }
            }
        }

        const addServer = async () => {
            try {
                await axios.post(`${API_BASE_URL}/api/servers`, newServer.value)
                emit('refresh')
                showAddServerModal.value = false
                newServer.value = { hostname: '', ip_address: '', app_id: null }
            } catch (error) {
                console.error('Error adding server:', error)
            }
        }

        const getApplicationName = (appId) => {
            const app = props.applications.find(a => a.id === appId)
            return app ? app.name : 'Unknown'
        }

        const getStatusClass = (status) => {
            switch (status) {
                case 'active':
                    return 'bg-green-100 text-green-800'
                case 'shutdown_pending':
                    return 'bg-yellow-100 text-yellow-800'
                case 'shutdown_verified':
                    return 'bg-blue-100 text-blue-800'
                default:
                    return 'bg-gray-100 text-gray-800'
            }
        }

        return {
            showAddServerModal,
            newServer,
            handleFileUpload,
            addServer,
            getApplicationName,
            getStatusClass
        }
    },
    props: ['servers', 'applications']
}

const SettingsComponent = {
    template: `<div class='bg-white rounded-lg shadow p-6'>
                    <h2 class='text-2xl font-bold mb-4'>Settings</h2>
                    <form @submit.prevent='saveSettings'>
                        <div class='mb-4'>
                            <label class='block text-sm font-medium text-gray-700'>Application Name</label>
                            <input v-model='appName' type='text' class='mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2' required />
                        </div>
                        <div class='mb-4'>
                            <label class='block text-sm font-medium text-gray-700'>Database URI</label>
                            <input v-model='dbURI' type='text' class='mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2' required />
                        </div>
                        <div class='mb-4'>
                            <label class='block text-sm font-medium text-gray-700'>API Base URL</label>
                            <input v-model='apiBaseURL' type='text' class='mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2' required />
                        </div>
                        <button type='submit' class='bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600'>Save Settings</button>
                    </form>
                </div>`,
    setup() {
        const appName = ref('Shutdown Manager')
        const dbURI = ref('sqlite:///shutdown_manager.db')
        const apiBaseURL = ref('http://localhost:5001')

        const saveSettings = () => {
            console.log('Settings saved:', { appName: appName.value, dbURI: dbURI.value, apiBaseURL: apiBaseURL.value })
            // Here you can implement the logic to save settings, e.g., to local storage or a backend API
        }

        return { appName, dbURI, apiBaseURL, saveSettings }
    }
}

// Router configuration
const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/', component: DashboardComponent, props: true },
        { path: '/applications', component: ApplicationsComponent, props: true },
        { path: '/servers', component: ServersComponent, props: true },
        { path: '/settings', component: SettingsComponent }
    ]
})

const app = createApp({
    setup() {
        const applications = ref([])
        const servers = ref([])

        // Computed properties
        const verifiedCount = computed(() => 
            applications.value.filter(app => app.shutdown_verified).length
        )
        const pendingCount = computed(() => 
            applications.value.filter(app => !app.shutdown_verified).length
        )

        const fetchApplications = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/api/applications`)
                applications.value = response.data
            } catch (error) {
                console.error('Error fetching applications:', error)
            }
        }

        const fetchServers = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/api/servers`)
                servers.value = response.data
            } catch (error) {
                console.error('Error fetching servers:', error)
            }
        }

        const fetchAll = () => {
            fetchApplications()
            fetchServers()
        }

        // Initial data fetch
        fetchAll()

        return {
            applications,
            servers,
            verifiedCount,
            pendingCount,
            fetchAll
        }
    }
})

app.use(router)
app.mount('#app')
