import React, { useState, useEffect } from 'react';
import './WikiPageList.css';

import { fetchWikiPages, deleteWikiPage } from '../../services/wikiService';

const WikiPageList = () => {
    const [wikiPages, setWikiPages] = useState([]);

    useEffect(() => {
        const fetchAndSetWikiPages = async () => {
            const wikiPages = await fetchWikiPages();
            setWikiPages(wikiPages);
        }

        fetchAndSetWikiPages();
    }, []);

    const handleDeletePage = async (id) => {
        try{ 
            await deleteWikiPage(id);
            const updatedWikiPages = wikiPages.filter((wikiPage) => wikiPage.id !== id);
            setWikiPages(updatedWikiPages);
        } catch (error) {
            console.error("Error deleting Wiki Page:", error);
        }
    }

    return (
        <div className="wiki-pages">
            {wikiPages.map((wikiPage) => (
                <WikiPage key={wikiPage.id} wikiPage={wikiPage} onDeleteWikiPage={handleDeletePage}/>
            ))}
        </div>
    );
}

const WikiPage = ({ wikiPage, onDeleteWikiPage }) => {
    return (
        <div className="wiki-page" id={wikiPage.id}>
            <div className="page-name">
                {wikiPage.name}
            </div>
            <div className="icons">
                <span id="delete" onClick={() => onDeleteWikiPage(wikiPage)}>✖</span>
                <i className="fa-solid fa-chart-simple"></i>
            </div>
        </div>
    );

}

export default WikiPageList;