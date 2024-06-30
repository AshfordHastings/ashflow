import React, { useEffect, useState } from 'react';

import './Home.css';
import WikiPageList from '../../components/WikiPageList/WikiPageList';

const Home = () => {
    return (
        <div className="page">
        <div className="header">
            <h2>
                Daily Wiki Page Info 
            </h2>
        </div>
        <WikiPageList />
    </div>
    )
}

export default Home;