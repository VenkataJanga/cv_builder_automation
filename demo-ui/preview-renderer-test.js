function assert(condition, message) {
    if (!condition) {
        throw new Error(message || 'Assertion failed');
    }
}

function runPreviewRendererTests() {
    const app = new CVBuilderApp({ autoInit: false });
    const cvData = {
        personal_details: {
            full_name: 'Test User',
            current_title: 'Engineering Lead',
            current_organization: 'NTT DATA',
            total_experience: 16,
            employee_id: '229164',
            email: 'test.user@nttdata.com',
            location: 'Pune',
        },
        summary: {
            professional_summary: 'Experienced leader in cloud and data engineering.',
        },
        education: [
            'Master of Computer Applications, ITM, Kakatiya University, 2007',
            'Bachelor of Science, Sri Chaitanya Degree College, Kakatiya University, 2004',
        ],
    };

    const results = [];

    try {
        const html = app.generateCVHTML(cvData);
        assert(html.includes('Test User'), 'Full name should render');
        assert(html.includes('Engineering Lead'), 'Title should render');
        assert(html.includes('Experienced leader in cloud and data engineering.'), 'Professional summary should render');
        assert(html.includes('Master of Computer Applications'), 'Education should render');

        const nestedSummaryData = {
            personal_details: {
                full_name: 'Nested User',
                current_title: 'Engineering Lead',
                current_organization: 'NTT DATA',
                total_experience: 16,
                employee_id: '229164',
                email: 'nested.user@nttdata.com',
                location: 'Pune',
            },
            summary: [
                { professional_summary: 'Experienced leader in cloud and data engineering.' }
            ],
            education: [
                'Master of Computer Applications, ITM, Kakatiya University, 2007',
            ],
        };

        const nestedHtml = app.generateCVHTML(nestedSummaryData);
        assert(nestedHtml.includes('Experienced leader in cloud and data engineering.'), 'Nested professional summary array should render');

        results.push({ message: 'All preview assertions passed.', status: 'pass' });
        document.getElementById('preview').innerHTML = html;
    } catch (error) {
        results.push({ message: error.message, status: 'fail' });
    }

    const output = document.getElementById('results');
    results.forEach(result => {
        const div = document.createElement('div');
        div.className = `result ${result.status}`;
        div.textContent = `${result.status.toUpperCase()}: ${result.message}`;
        output.appendChild(div);
    });
}

window.addEventListener('DOMContentLoaded', runPreviewRendererTests);
