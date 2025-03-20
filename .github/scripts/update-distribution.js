const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const toml = require('toml');

// Get inputs from command-line arguments
const DISTRIBUTION_URL = process.argv[2]; // First argument: Distribution URL
const API_KEY = process.argv[3]; // Second argument: API Key
const SLUG = process.argv[4]; // Third argument: Slug
const FILE_PATH = process.argv[5]; // Fourth argument: File path
const TOML_FILE_PATH = process.argv[6]; // Fourth argument: File path

if (!DISTRIBUTION_URL || !API_KEY || !SLUG || !FILE_PATH) {
    console.error('Usage: node update-distribution.js <DISTRIBUTION_URL> <API_KEY> <SLUG> <FILE_PATH>');
    process.exit(1);
}

async function uploadBlenderPackageFile() {
    try {
        // Create form data
        const form = new FormData();
        form.append('file', fs.createReadStream(FILE_PATH), {
            contentType: 'application/x-zip-compressed',
        });

        // Make the POST request
        const response = await axios.post(
            `${DISTRIBUTION_URL}/api/blender-package`,
            form,
            {
                headers: {
                    ...form.getHeaders(),
                    Authorization: `users API-Key ${API_KEY}`,
                },
            }
        );

        // Extract the ID from the response
        const packageId = response.data?.doc?.id;
        return packageId;
    } catch (error) {
        console.error('Error uploading file:', error.response?.data || error.message);
        process.exit(1);
    }
}

async function updateBlender(packageId) {
    try {
        // Read and parse the TOML file
        const tomlContent = fs.readFileSync(TOML_FILE_PATH, 'utf-8');
        const data = { ...toml.parse(tomlContent) };

        delete data.id;
        data.license = (data.license || []).map((license) => ({
            value: license,
        }));
        data.package = packageId;

        console.log('Updating Blender package with data:', data);

        await axios.patch(
            `${DISTRIBUTION_URL}/api/blender?where[slug][equals]=${SLUG}`,
            data,
            {
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `users API-Key ${API_KEY}`,
                },
            }
        );

        console.log('Blender package updated successfully');
        process.exit(0);

    } catch (error) {
        console.error('Error updating Blender:', error.response?.data || error.message);
        process.exit(1);
    }
}

(async () => {
    const packageId = await uploadBlenderPackageFile();
    await updateBlender(packageId);
})();


