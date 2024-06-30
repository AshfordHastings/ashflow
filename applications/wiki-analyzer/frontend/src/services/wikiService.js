import axios from 'axios';

export const fetchWikiPages = async () => {
    const response = await axios.get('/api/wiki-pages');
    return response.data;
}

export const deleteWikiPage = async (id) => {
    const response = await axios.delete(`/api/wiki-pages/${id}`);
    return response.data;
}