

            const url = location.href
            console.warn('404',url)
            try {
                // Process URL components


                
                const urlSegments = url.split('/').filter(Boolean);
                let [origin, item] = urlSegments.slice(-2);
                const baseURL = url.substring(0, url.lastIndexOf('/') + 1);


                // console.warn(baseURL,window.location.origin, origin)
                if (baseURL === location.origin || origin === 'src-data'){
                    console.log(origin,item)
                    origin = item
                }
                
                const jsonURL = `${baseURL}${item}.json`;
                const readmeURL = `${baseURL}README.md`;
                
                console.log(baseURL)
                
                // Attempt to fetch JSON data for the current item

                if (!url.endsWith('.json')){
                let response = await fetch(jsonURL);
                if (response.ok) {
                    // throw new Error(`JSON file not found. Displaying default view.`);
                    window.location.href = jsonURL;
                }
                console.log(`json file does not exist: ${jsonURL}`)
                };
            





            // Configure Prism autoloader path
                window.Prism = window.Prism || {};
                window.Prism.manual = true;
                
                // Load markdown from file
                fetch(readmeURL) // <-- Replace with your .md file path or URL
                .then(response => response.text())
                .then(markdown => {
                    // Parse markdown and insert into DOM
                    document.getElementById('content').innerHTML = marked.parse(markdown);
                    
                    // Trigger Prism syntax highlighting after content is loaded
                    if (window.Prism) {
                    Prism.highlightAll();
                    }
                })
                .catch(error => {
                    document.getElementById('content').innerHTML = "<p>Error loading markdown file.</p>";
                    console.error("Error loading markdown:", error);
                });

            } catch (error) {
                console.error("Error fetching or processing data:", error);
                document.getElementById('content').innerHTML = "<p>Error fetching or processing data. This URL and directory does not have an associated README or json file. </p>";
            }