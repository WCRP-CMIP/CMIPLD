async function fetchAndDisplayData(location) {

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
                const schemaURL = `${baseURL}_schema`
                            // .replace('//','/');
                console.log(baseURL)
                
                // Set title with link back to base URL
                document.getElementById('title').innerHTML = `<a href=${baseURL}>${origin}</a> : ${item}`;

                // Attempt to fetch JSON data for the current item

                if (!url.endsWith('.json')){
                let response = await fetch(jsonURL);
                if (response.ok) {
                    // throw new Error(`JSON file not found. Displaying default view.`);
                    window.location.href = jsonURL;
                }
                console.log(`json file does not exist: ${jsonURL}`)
                }


                // Build display HTML
                let contentHTML = ''
                
                // trying to get schema.
                response = await fetch(schemaURL);
                // Parse JSON data
                const data = await response.json();

                console.log(data)
                
                const itemData = data.properties[item];
                
                if (!itemData) {

                    response = await fetch(`${baseURL}_context`);
                    const context = await response.json();
                    

                    console.log(context)
                    // document.getElementById('content').innerHTML = 'blank'

                    document.getElementById('title').innerHTML = `<a href=${baseURL}>${origin}</a>`;
                    
                    contentHTML += `<h2>Parent</h2><p>${data.prefix} : <a href=${baseURL}>${origin}</a></p>`
                    
                    const github = `${data.repo}/tree/main/src-data/${origin}`
                    contentHTML += `<h2>GithubURL</h2><p><a href=${github}>${data.repo.split('github.com/')[1]}</a></p>`


                     if (data.references) {
                        contentHTML += `<h2>Linked To</h2> <ul>`;
                        data.references.forEach(link => {
                            contentHTML += `<li><a href="${link}" target="_blank">${link}</a></li>`;
                        });
                    contentHTML += `</ul>`;
                }


                if (context) {
                    
                       let strcontext = JSON.stringify(context, null,4)
                            .replaceAll('\n', '<br>') // Inserts <br> tags
                            .replaceAll('  ', '&ensp;&ensp;'); // Replaces spaces with &ensp;
                        
                        contentHTML += `<h2>Context</h2><pre><code>${strcontext}</code></pre>`;
                                                
                }
    
                contentHTML += `<h2>Fields</h2> <ul>`;
                        Object.keys(data.properties).forEach(key => {
                            contentHTML += `<li><a href="${baseURL}${key}" target="_blank">${key}</a></li>`;
                        });
                contentHTML += `</ul>`;

                    
                    
                    // throw new Error("Item not found in schema data.");
                    
                }
                else {
                

                contentHTML += `<h2>Parent</h2><p>${data.prefix} : <a href=${baseURL}>${origin}</a></p>`

                const github = `${data.repo}/tree/main/src-data/${origin}`
                contentHTML += `<h2>GithubURL</h2><p><a href=${github}>${data.repo.split('github.com/')[1]}</a></p>`
                    
                    
                contentHTML += `<h2>Description</h2><p>${itemData.description || "No description available."}</p>`;
                
                // Display types with schema.org links if available
                if (itemData.type) {
                    contentHTML += `<h2>Types</h2><ul>`;
                    if (!(itemData.type instanceof Array)) itemData.type = [itemData.type]
                    
                    itemData.type.forEach(type => {
                        contentHTML += `<li><a href="https://schema.org/${type}" target="_blank">${type}</a></li>`;
                    });
                    contentHTML += `</ul>`;
                }

                // Display links if available
                if (itemData.links) {
                    contentHTML += `<h2>Related Links</h2> <ul>`;
                    itemData.links.forEach(link => {
                        contentHTML += `<li><a href="${link.url}" target="_blank">${link.name}</a></li>`;
                    });
                    contentHTML += `</ul>`;
                }

            }
                // Display the final content
                document.getElementById('content').innerHTML = contentHTML;
            } catch (error) {
                // Display 404 page if JSON not found or item does not exist
                document.getElementById('content').innerHTML = `<p style="color: red;">404 Not Found: ${error.message}</p>`;
                console.error(error)
            }
        }

        // Example usage with URL input
        // const exampleURL = "https://wcrp-cmip.github.io/CMIP6Plus_MIP_variables/src-data/variables/cell_measures";
        fetchAndDisplayData(window.location);
