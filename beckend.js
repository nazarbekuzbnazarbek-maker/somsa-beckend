async function loadDataFromBackend() {
    try {
        let response = await fetch('SIZNING_BACKEND_URL/api/init-data');
        let data = await response.json();
        
        // Olingan ma'lumotlarni ilovaga yuklash
        users = data.users;
        somsaTypes = data.somsaTypes;
        productionLogs = data.productionLogs;
        salesLogs = data.salesLogs;
        auditRequests = data.auditRequests;
        cardNumber = data.cardNumber;
        
        refreshAllUI();
    } catch (e) {
        console.error("Server bilan ulanishda xatolik:", e);
    }
}
