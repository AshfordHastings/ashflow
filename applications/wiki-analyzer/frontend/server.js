const express = require('express');
const webpack = require('webpack');
const webpackDevMiddleware = require('webpack-dev-middleware');
const path = require('path');

const app = express();
const config = require('./webpack.config.js');
const compiler = webpack(config);

// Tell express to use the webpack-dev-middleware and use the webpack.config.js
// configuration file as a base.
app.use(
  webpackDevMiddleware(compiler, {
    publicPath: config.output.publicPath, // The public path determines the prefix of the URL for the webpack assets referenced in requests. I think.
  })
);

app.use(express.static(path.join(__dirname, 'dist')));

// Serve the files on port 3000.
app.listen(3001, function () {
  console.log('Example app listening on port 3000!\n');
});

const mockWikiPageData = [
  { id: 1, name: 'Amazon' },
  { id: 2, name: 'Google' },
  { id: 3, name: 'Facebook' },
  { id: 4, name: 'Apple' },
  { id: 5, name: 'Microsoft' }
]

app.get('/api/wiki-pages', (req, res) => {
  res.json(mockWikiPageData);
});

app.delete('/api/wiki-pages/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const updatedWikiPages = mockWikiPageData.filter((wikiPage) => wikiPage.id !== id);
  mockWikiPageData.length = 0;
  mockWikiPageData.push(...updatedWikiPages);
  res.json(updatedWikiPages);
});